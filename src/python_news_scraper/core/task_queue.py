import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import uuid4
from pydantic import BaseModel
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
from .logging_handler import get_logger

logger = get_logger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    SCRAPE_ALL = "scrape_all"
    SCRAPE_SOURCE = "scrape_source"
    PERIODIC_SCRAPE = "periodic_scrape"


class TaskInfo(BaseModel):
    id: str
    task_type: TaskType
    status: TaskStatus
    source: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: float = 0.0


class TaskQueue:
    """
    Robust task queue system similar to Quartz scheduler.
    Handles concurrent background jobs with proper monitoring and management.
    """
    
    def __init__(self):
        # Configure APScheduler with proper settings
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': ThreadPoolExecutor(max_workers=10)  # Allow concurrent jobs
        }
        job_defaults = {
            'coalesce': True,  # Combine multiple instances of same job
            'max_instances': 3,  # Max concurrent instances per job
            'misfire_grace_time': 300  # Grace time for missed jobs (5 min)
        }
        
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )
        
        # Task tracking
        self.tasks: Dict[str, TaskInfo] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        
        # Setup event listeners
        self._setup_listeners()
    
    def _setup_listeners(self):
        """Setup APScheduler event listeners for task monitoring."""
        self.scheduler.add_listener(
            self._job_executed_listener,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED
        )
    
    def _job_executed_listener(self, event):
        """Handle scheduler events for task status updates."""
        job_id = event.job_id
        if job_id in self.tasks:
            task = self.tasks[job_id]
            
            if event.exception:
                task.status = TaskStatus.FAILED
                task.error = str(event.exception)
                task.completed_at = datetime.utcnow()
                logger.error(f"Task {job_id} failed: {event.exception}")
            else:
                task.status = TaskStatus.COMPLETED
                task.result = getattr(event, 'retval', None)
                task.completed_at = datetime.utcnow()
                logger.info(f"Task {job_id} completed successfully")
    
    async def start(self):
        """Start the task queue system."""
        try:
            self.scheduler.start()
            logger.info("Task queue system started successfully")
            
            # Schedule the initial periodic scraping job
            await self.schedule_periodic_scraping()
            
        except Exception as e:
            logger.error(f"Failed to start task queue: {e}")
            raise
    
    async def stop(self):
        """Stop the task queue system."""
        try:
            # Cancel all running tasks
            for task_id, task in self.running_tasks.items():
                if not task.done():
                    task.cancel()
                    if task_id in self.tasks:
                        self.tasks[task_id].status = TaskStatus.CANCELLED
            
            self.scheduler.shutdown(wait=True)
            logger.info("Task queue system stopped")
            
        except Exception as e:
            logger.error(f"Error stopping task queue: {e}")
    
    async def add_task(
        self,
        task_type: TaskType,
        task_func,
        source: Optional[str] = None,
        run_immediately: bool = True,
        schedule_info: Optional[Dict] = None,
        **kwargs
    ) -> str:
        """
        Add a new task to the queue.
        
        Args:
            task_type: Type of task
            task_func: Async function to execute
            source: Source name for scraping tasks
            run_immediately: Run now or schedule for later
            schedule_info: Scheduling information for recurring tasks
            **kwargs: Additional arguments for the task function
        
        Returns:
            Task ID
        """
        task_id = str(uuid4())
        
        # Create task info
        task_info = TaskInfo(
            id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            source=source,
            created_at=datetime.utcnow()
        )
        self.tasks[task_id] = task_info
        
        if run_immediately:
            # Run immediately as background task
            background_task = asyncio.create_task(
                self._execute_task(task_id, task_func, **kwargs)
            )
            self.running_tasks[task_id] = background_task
            
        elif schedule_info:
            # Schedule for later execution
            trigger = self._create_trigger(schedule_info)
            self.scheduler.add_job(
                func=self._execute_task,
                trigger=trigger,
                args=[task_id, task_func],
                kwargs=kwargs,
                id=task_id,
                replace_existing=True
            )
        
        logger.info(f"Added task {task_id} of type {task_type}")
        return task_id
    
    def _create_trigger(self, schedule_info: Dict):
        """Create APScheduler trigger from schedule info."""
        schedule_type = schedule_info.get('type', 'interval')
        
        if schedule_type == 'interval':
            # Only pass non-None values to avoid timedelta errors
            interval_kwargs = {
                k: v for k, v in {
                    'seconds': schedule_info.get('seconds'),
                    'minutes': schedule_info.get('minutes'),
                    'hours': schedule_info.get('hours'),
                    'days': schedule_info.get('days')
                }.items() if v is not None
            }
            return IntervalTrigger(**interval_kwargs)
        elif schedule_type == 'cron':
            return CronTrigger(
                hour=schedule_info.get('hour'),
                minute=schedule_info.get('minute'),
                day=schedule_info.get('day'),
                month=schedule_info.get('month'),
                day_of_week=schedule_info.get('day_of_week')
            )
        elif schedule_type == 'date':
            return DateTrigger(
                run_date=schedule_info.get('run_date')
            )
        else:
            raise ValueError(f"Unsupported schedule type: {schedule_type}")
    
    async def _execute_task(self, task_id: str, task_func, **kwargs):
        """Execute a task with proper error handling and status tracking."""
        task_info = self.tasks.get(task_id)
        if not task_info:
            logger.error(f"Task {task_id} not found")
            return
        
        try:
            # Update task status
            task_info.status = TaskStatus.RUNNING
            task_info.started_at = datetime.utcnow()
            
            logger.info(f"Starting execution of task {task_id}")
            
            # Execute the task function
            if asyncio.iscoroutinefunction(task_func):
                result = await task_func(**kwargs)
            else:
                result = task_func(**kwargs)
            
            # Update task with results
            task_info.status = TaskStatus.COMPLETED
            task_info.completed_at = datetime.utcnow()
            task_info.result = {"articles_scraped": result} if isinstance(result, int) else result
            task_info.progress = 1.0
            
            logger.info(f"Task {task_id} completed successfully")
            return result
            
        except Exception as e:
            # Handle task failure
            task_info.status = TaskStatus.FAILED
            task_info.error = str(e)
            task_info.completed_at = datetime.utcnow()
            
            logger.error(f"Task {task_id} failed: {e}", exc_info=True)
            raise
            
        finally:
            # Clean up running task reference
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
    
    async def schedule_periodic_scraping(self):
        """Schedule periodic scraping of all sources."""
        # Import here to avoid circular imports
        from ..api.services.scraping_service import scraping_service
        
        # Schedule periodic scraping every 2 hours
        schedule_info = {
            'type': 'interval',
            'hours': 2
        }
        
        task_id = await self.add_task(
            task_type=TaskType.PERIODIC_SCRAPE,
            task_func=scraping_service.scrape_all_sources,
            run_immediately=False,  # Don't run immediately on startup
            schedule_info=schedule_info
        )
        
        logger.info(f"Scheduled periodic scraping task {task_id}")
        return task_id
    
    async def scrape_all_sources_now(self) -> str:
        """Manually trigger scraping of all sources."""
        from ..api.services.scraping_service import scraping_service
        
        task_id = await self.add_task(
            task_type=TaskType.SCRAPE_ALL,
            task_func=scraping_service.scrape_all_sources,
            run_immediately=True
        )
        
        logger.info(f"Triggered manual scraping of all sources: {task_id}")
        return task_id
    
    async def scrape_source_now(self, source: str) -> str:
        """Manually trigger scraping of a specific source."""
        from ..api.services.scraping_service import scraping_service
        
        task_id = await self.add_task(
            task_type=TaskType.SCRAPE_SOURCE,
            task_func=scraping_service.scrape_source,
            source=source,
            run_immediately=True,
            **{"source": source}  # Pass source as kwarg to the function
        )
        
        logger.info(f"Triggered manual scraping of source {source}: {task_id}")
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """Get status of a specific task."""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[TaskInfo]:
        """Get status of all tasks."""
        return list(self.tasks.values())
    
    def get_running_tasks(self) -> List[TaskInfo]:
        """Get all currently running tasks."""
        return [task for task in self.tasks.values() if task.status == TaskStatus.RUNNING]
    
    def get_tasks_by_type(self, task_type: TaskType) -> List[TaskInfo]:
        """Get all tasks of a specific type."""
        return [task for task in self.tasks.values() if task.task_type == task_type]
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            if not task.done():
                task.cancel()
                if task_id in self.tasks:
                    self.tasks[task_id].status = TaskStatus.CANCELLED
                    self.tasks[task_id].completed_at = datetime.utcnow()
                logger.info(f"Cancelled task {task_id}")
                return True
        
        # Try to remove from scheduler
        try:
            self.scheduler.remove_job(task_id)
            if task_id in self.tasks:
                self.tasks[task_id].status = TaskStatus.CANCELLED
                self.tasks[task_id].completed_at = datetime.utcnow()
            logger.info(f"Removed scheduled task {task_id}")
            return True
        except Exception:
            pass
        
        return False
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Clean up old completed/failed tasks."""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        tasks_to_remove = []
        
        for task_id, task in self.tasks.items():
            if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] 
                and task.completed_at 
                and task.completed_at < cutoff_time):
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
        
        if tasks_to_remove:
            logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")


# Global task queue instance
task_queue = TaskQueue()