"""
Loguru logging configuration for Czech News Scraper.
Provides async-safe, thread-safe logging with proper formatting and rotation.
"""

import sys
from pathlib import Path
from loguru import logger
from typing import Optional, Dict, Any
import asyncio
import functools


class LoggingHandler:
    """
    Centralized logging configuration using Loguru.
    Handles async/await compatibility, thread safety, and proper formatting.
    """
    
    def __init__(self):
        self._configured = False
        self._log_dir = Path("logs")
        self._log_dir.mkdir(exist_ok=True)
    
    def configure_logging(
        self,
        log_level: str = "INFO",
        log_to_file: bool = True,
        log_to_console: bool = True,
        enable_json: bool = False,
        enable_rotation: bool = True
    ) -> None:
        """
        Configure Loguru logger with async-safe settings.
        
        Args:
            log_level: Minimum logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_to_file: Whether to log to files
            log_to_console: Whether to log to console
            enable_json: Whether to use JSON serialization for structured logging
            enable_rotation: Whether to enable log file rotation
        """
        if self._configured:
            return
        
        # Remove default handler to avoid conflicts
        logger.remove()
        
        # Configure console logging
        if log_to_console:
            console_format = (
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            )
            
            logger.add(
                sys.stderr,
                level=log_level,
                format=console_format,
                colorize=True,
                enqueue=True,  # Thread-safe logging
                catch=True,    # Catch logging errors
                backtrace=True,
                diagnose=True
            )
        
        # Configure file logging
        if log_to_file:
            file_format = (
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
                "{level: <8} | "
                "{name}:{function}:{line} | "
                "{message}"
            )
            
            # Main application log
            main_log_config = {
                "level": log_level,
                "format": file_format,
                "enqueue": True,  # Essential for async/thread safety
                "catch": True,
                "backtrace": True,
                "diagnose": True,
                "serialize": enable_json
            }
            
            if enable_rotation:
                main_log_config.update({
                    "rotation": "10 MB",  # Rotate when file reaches 10MB
                    "retention": "7 days",  # Keep logs for 7 days
                    "compression": "zip"    # Compress old logs
                })
            
            logger.add(
                self._log_dir / "news_scraper.log",
                **main_log_config
            )
            
            # Separate log for scraping activities
            scraping_log_config = main_log_config.copy()
            scraping_log_config["filter"] = lambda record: "scraping" in record["name"].lower()
            
            logger.add(
                self._log_dir / "scraping.log",
                **scraping_log_config
            )
            
            # Error-only log for monitoring
            error_log_config = main_log_config.copy()
            error_log_config["level"] = "ERROR"
            
            logger.add(
                self._log_dir / "errors.log",
                **error_log_config
            )
        
        # Set up async completion handling
        self._setup_async_handling()
        
        self._configured = True
        logger.info("Logging system configured successfully")
    
    def _setup_async_handling(self) -> None:
        """
        Set up proper async handling for logging operations.
        Prevents race conditions and ensures proper cleanup.
        """
        # Bind async context information
        logger.configure(
            extra={
                "app_name": "czech_news_scraper",
                "version": "0.1.0"
            }
        )
    
    async def shutdown_logging(self) -> None:
        """
        Properly shutdown logging system, ensuring all messages are flushed.
        Should be called during application shutdown.
        """
        try:
            # Wait for all enqueued messages to be processed
            await logger.complete()
            logger.info("Logging system shutdown completed")
        except Exception as e:
            # Fallback to sync logging if async fails
            logger.error(f"Error during logging shutdown: {e}")
    
    def get_logger(self, name: Optional[str] = None) -> Any:
        """
        Get a logger instance with optional name binding.
        
        Args:
            name: Optional name to bind to the logger
            
        Returns:
            Configured logger instance
        """
        if name:
            return logger.bind(module=name)
        return logger
    
    def async_catch(self, reraise: bool = False, level: str = "ERROR"):
        """
        Decorator for async functions to catch and log exceptions.
        Thread-safe and async-compatible version of logger.catch().
        
        Args:
            reraise: Whether to reraise the exception after logging
            level: Log level for caught exceptions
            
        Returns:
            Decorator function
        """
        def decorator(func):
            if asyncio.iscoroutinefunction(func):
                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        logger.log(level, f"Exception in {func.__name__}: {e}")
                        if reraise:
                            raise
                        return None
                return async_wrapper
            else:
                @functools.wraps(func)
                def sync_wrapper(*args, **kwargs):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        logger.log(level, f"Exception in {func.__name__}: {e}")
                        if reraise:
                            raise
                        return None
                return sync_wrapper
        return decorator


# Global logging handler instance
logging_handler = LoggingHandler()

# Convenience functions for easy access
def get_logger(name: Optional[str] = None):
    """Get a configured logger instance."""
    return logging_handler.get_logger(name)

def configure_logging(**kwargs):
    """Configure the logging system."""
    return logging_handler.configure_logging(**kwargs)

async def shutdown_logging():
    """Shutdown the logging system properly."""
    await logging_handler.shutdown_logging()

def async_catch(**kwargs):
    """Async-safe exception catching decorator."""
    return logging_handler.async_catch(**kwargs)