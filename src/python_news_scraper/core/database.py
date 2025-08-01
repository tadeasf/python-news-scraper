import aiosqlite
from sqlmodel import SQLModel, create_engine, Session
from typing import AsyncGenerator
import os

# Import all models to ensure they're registered with SQLModel
from .models import (
    Article, Entity, ArticleEntity, Topic, ArticleTopic, 
    SentimentAnalysis
)

DATABASE_URL = "sqlite:///./news_scraper.db"

engine = create_engine(DATABASE_URL, echo=True)


async def create_db_and_tables():
    """Create database tables."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Get database session."""
    return Session(engine)


def get_database_url():
    """Get the database URL."""
    return DATABASE_URL


async def get_async_session():
    """Get async database session."""
    # For async operations, we'll use aiosqlite directly when needed
    async with aiosqlite.connect("news_scraper.db") as db:
        yield db