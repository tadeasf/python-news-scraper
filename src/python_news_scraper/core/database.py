import aiosqlite
from sqlmodel import SQLModel, create_engine, Session
from typing import AsyncGenerator
import os

DATABASE_URL = "sqlite:///./news_scraper.db"

engine = create_engine(DATABASE_URL, echo=True)


async def create_db_and_tables():
    """Create database tables."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Get database session."""
    with Session(engine) as session:
        yield session


async def get_async_session():
    """Get async database session."""
    # For async operations, we'll use aiosqlite directly when needed
    async with aiosqlite.connect("news_scraper.db") as db:
        yield db