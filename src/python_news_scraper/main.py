from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .core.database import create_db_and_tables
from .core.migration import run_migrations
from .api.routes.articles import router as articles_router
from .api.routes.search import router as search_router
from .api.routes.nlp import router as nlp_router
from .api.services.nlp.nlp_service import nlp_service
from .core.scheduler import start_scheduler, stop_scheduler
from .core.logging_handler import configure_logging, get_logger, shutdown_logging

# Configure Loguru logging
configure_logging(
    log_level="INFO",
    log_to_file=True,
    log_to_console=True,
    enable_json=False,
    enable_rotation=True
)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Czech News Scraper...")
    
    # Create database tables
    await create_db_and_tables()
    logger.info("Database initialized")
    
    # Run database migrations
    run_migrations()
    logger.info("Database migrations completed")
    
    # Start background scheduler
    await start_scheduler()
    logger.info("Background scheduler started")
    
    # Initialize NLP service (this might take a while on first run)
    try:
        await nlp_service.initialize()
        logger.info("NLP service initialized successfully")
    except Exception as e:
        logger.warning(f"NLP service initialization failed: {e}. NLP features will be unavailable.")
    
    yield
    
    # Shutdown
    await stop_scheduler()
    logger.info("Background scheduler stopped")
    
    # Properly shutdown logging system
    await shutdown_logging()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Czech News Scraper",
    description="Automatický sběr zpráv z českých zpravodajských portálů",
    version="0.1.0",
    lifespan=lifespan
)

# Include routers
app.include_router(articles_router)
app.include_router(search_router)
app.include_router(nlp_router)

# Mount static files (if needed in the future)
# app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Czech News Scraper is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.python_news_scraper.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
