import asyncio
from .task_queue import task_queue
from .logging_handler import get_logger

logger = get_logger(__name__)


async def start_scheduler():
    """Start the background task queue system."""
    try:
        await task_queue.start()
        logger.info("Background task queue started successfully")
        
        # Trigger initial scraping after startup (after 30 seconds)
        asyncio.create_task(initial_scrape_after_startup())
        
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        raise


async def stop_scheduler():
    """Stop the background task queue system."""
    try:
        await task_queue.stop()
        logger.info("Background task queue stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")


async def initial_scrape_after_startup():
    """Trigger initial scraping 30 seconds after startup."""
    try:
        # Wait 30 seconds for the app to fully initialize
        await asyncio.sleep(30)
        
        logger.info("Triggering initial scraping after startup")
        task_id = await task_queue.scrape_all_sources_now()
        logger.info(f"Initial scraping task started with ID: {task_id}")
        
    except Exception as e:
        logger.error(f"Error during initial scraping: {e}")


# Legacy functions for backward compatibility
def start_scheduler_sync():
    """Synchronous wrapper for starting scheduler."""
    loop = asyncio.get_event_loop()
    return loop.create_task(start_scheduler())


def stop_scheduler_sync():
    """Synchronous wrapper for stopping scheduler."""
    loop = asyncio.get_event_loop()
    return loop.create_task(stop_scheduler())