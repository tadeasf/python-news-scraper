from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func, or_
from typing import Optional, List
from ...core.database import get_session
from ...core.models import Article
from ...api.services.scraping_service import scraping_service
from ...core.task_queue import task_queue, TaskType, TaskStatus
from ...core.logging_handler import get_logger

logger = get_logger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="src/python_news_scraper/templates")


@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    source: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    session: Session = Depends(get_session)
):
    """Homepage showing scraped articles with filtering and search."""
    # Check if this is an HTMX request for partial content
    is_htmx_request = request.headers.get("HX-Request") == "true"
    
    offset = (page - 1) * limit
    
    # Build query
    query = select(Article)
    
    # Apply filters
    if source:
        query = query.where(Article.source == source)
    
    if search:
        search_filter = or_(
            Article.title.contains(search),
            Article.perex.contains(search)
        )
        query = query.where(search_filter)
    
    # Order by scraped_at descending
    query = query.order_by(Article.scraped_at.desc())
    
    # Get total count for pagination
    count_query = select(func.count(Article.id))
    if source:
        count_query = count_query.where(Article.source == source)
    if search:
        count_query = count_query.where(search_filter)
    
    total_articles = session.exec(count_query).one()
    
    # Get articles for current page
    articles_query = query.offset(offset).limit(limit)
    articles = session.exec(articles_query).all()
    
    # Calculate pagination info
    total_pages = (total_articles + limit - 1) // limit
    has_previous = page > 1
    has_next = page < total_pages
    
    # Get available sources for filter dropdown
    sources_query = select(Article.source).distinct()
    available_sources = session.exec(sources_query).all()
    
    context = {
        "request": request,
        "articles": articles,
        "page": page,
        "total_pages": total_pages,
        "has_previous": has_previous,
        "has_next": has_next,
        "total_articles": total_articles,
        "current_source": source,
        "current_search": search or "",
        "available_sources": available_sources,
        "limit": limit
    }
    
    # Return only articles list for HTMX requests, full page for regular requests
    if is_htmx_request:
        return templates.TemplateResponse("articles_list.html", context)
    else:
        return templates.TemplateResponse("index.html", context)


@router.post("/scrape", response_class=HTMLResponse)
async def manual_scrape(
    request: Request,
    source: Optional[str] = Query(None),
    session: Session = Depends(get_session)
):
    """Manually trigger scraping for all sources or a specific source."""
    try:
        if source:
            valid_sources = ['aktualne', 'novinky', 'idnes', 'ihned', 'seznamzpravy', 'blesk', 'ct24', 'irozhlas', 'lidovky', 'denik', 'forum24', 'e15']
            if source not in valid_sources:
                return templates.TemplateResponse("scrape_result.html", {
                    "request": request,
                    "success": False,
                    "message": f"Unknown source: {source}",
                    "articles_count": 0,
                    "task_id": None
                })
            
            # Use task queue for concurrent scraping
            task_id = await task_queue.scrape_source_now(source)
            message = f"Started scraping task for {source}. Task ID: {task_id}"
        else:
            # Use task queue for concurrent scraping
            task_id = await task_queue.scrape_all_sources_now()
            message = f"Started scraping task for all sources. Task ID: {task_id}"
        
        return templates.TemplateResponse("scrape_result.html", {
            "request": request,
            "success": True,
            "message": message,
            "articles_count": 0,  # Will be updated when task completes
            "task_id": task_id
        })
        
    except Exception as e:
        logger.error(f"Error during manual scrape: {e}")
        return templates.TemplateResponse("scrape_result.html", {
            "request": request,
            "success": False,
            "message": f"Error starting scraping task: {str(e)}",
            "articles_count": 0,
            "task_id": None
        })


@router.get("/api/articles")
async def get_articles_api(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    source: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    session: Session = Depends(get_session)
):
    """API endpoint to get articles as JSON."""
    offset = (page - 1) * limit
    
    # Build query
    query = select(Article)
    
    # Apply filters
    if source:
        query = query.where(Article.source == source)
    
    if search:
        search_filter = or_(
            Article.title.contains(search),
            Article.perex.contains(search)
        )
        query = query.where(search_filter)
    
    # Order by scraped_at descending
    query = query.order_by(Article.scraped_at.desc())
    
    # Get total count
    count_query = select(func.count(Article.id))
    if source:
        count_query = count_query.where(Article.source == source)
    if search:
        count_query = count_query.where(search_filter)
    
    total_articles = session.exec(count_query).one()
    
    # Get articles for current page
    articles_query = query.offset(offset).limit(limit)
    articles = session.exec(articles_query).all()
    
    return {
        "articles": articles,
        "page": page,
        "limit": limit,
        "total": total_articles,
        "total_pages": (total_articles + limit - 1) // limit
    }


@router.get("/api/tasks")
async def get_tasks():
    """Get all tasks with their current status."""
    tasks = task_queue.get_all_tasks()
    return {
        "tasks": [task.model_dump() for task in tasks],
        "total": len(tasks)
    }


@router.get("/api/tasks/running")
async def get_running_tasks():
    """Get all currently running tasks."""
    running_tasks = task_queue.get_running_tasks()
    return {
        "tasks": [task.model_dump() for task in running_tasks],
        "total": len(running_tasks)
    }


@router.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get status of a specific task."""
    task = task_queue.get_task_status(task_id)
    if not task:
        return {"error": "Task not found"}, 404
    return task.model_dump()


@router.post("/api/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    """Cancel a running task."""
    success = await task_queue.cancel_task(task_id)
    if success:
        return {"message": f"Task {task_id} cancelled successfully"}
    else:
        return {"error": "Task not found or already completed"}, 404


@router.post("/api/scrape/schedule")
async def schedule_scraping(
    source: Optional[str] = None,
    schedule_type: str = "interval",
    hours: Optional[int] = None,
    minutes: Optional[int] = None,
    cron_expression: Optional[str] = None
):
    """Schedule a scraping task."""
    try:
        schedule_info = {"type": schedule_type}
        
        if schedule_type == "interval":
            if hours:
                schedule_info["hours"] = hours
            if minutes:
                schedule_info["minutes"] = minutes
        elif schedule_type == "cron" and cron_expression:
            # Parse cron expression (simplified)
            parts = cron_expression.split()
            if len(parts) >= 2:
                schedule_info["minute"] = parts[0]
                schedule_info["hour"] = parts[1]
        
        task_type = TaskType.SCRAPE_SOURCE if source else TaskType.SCRAPE_ALL
        
        if source:
            task_id = await task_queue.add_task(
                task_type=task_type,
                task_func=scraping_service.scrape_source,
                source=source,
                run_immediately=False,
                schedule_info=schedule_info,
                **{"source": source}  # Pass source as kwarg to the function
            )
        else:
            task_id = await task_queue.add_task(
                task_type=task_type,
                task_func=scraping_service.scrape_all_sources,
                run_immediately=False,
                schedule_info=schedule_info
            )
        
        return {
            "message": "Scraping task scheduled successfully",
            "task_id": task_id,
            "schedule": schedule_info
        }
        
    except Exception as e:
        logger.error(f"Error scheduling scraping task: {e}")
        return {"error": f"Failed to schedule task: {str(e)}"}, 500