from datetime import datetime
from typing import Optional
import hashlib
from sqlmodel import SQLModel, Field, Index


class ArticleBase(SQLModel):
    title: str = Field(index=True)  # Index for faster searching
    perex: str  # Article summary/excerpt
    source: str = Field(index=True)  # News website name
    url: str = Field(index=True)  # URL should be unique (removed unique constraint temporarily)
    title_hash: str = Field(default="", index=True)  # Hash of normalized title for duplicate detection
    scraped_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)  # Track updates
    

class Article(ArticleBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Ensure we have indexes for common queries
    __table_args__ = (
        Index("idx_source_scraped", "source", "scraped_at"),
        Index("idx_title_hash_source", "title_hash", "source"),
    )
    

class ArticleCreate(SQLModel):
    title: str
    perex: str
    source: str
    url: str
    
    def to_article_base(self) -> ArticleBase:
        """Convert to ArticleBase with computed fields."""
        # Normalize title for duplicate detection
        normalized_title = self.title.lower().strip()
        # Remove common punctuation and extra spaces
        import re
        normalized_title = re.sub(r'[^\w\s]', '', normalized_title)
        normalized_title = re.sub(r'\s+', ' ', normalized_title)
        
        # Create hash for duplicate detection
        title_hash = hashlib.md5(normalized_title.encode('utf-8')).hexdigest()
        
        return ArticleBase(
            title=self.title,
            perex=self.perex,
            source=self.source,
            url=self.url,
            title_hash=title_hash
        )


class ArticleRead(ArticleBase):
    id: int