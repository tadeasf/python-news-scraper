from datetime import datetime
from typing import Optional, List
import hashlib
from sqlmodel import SQLModel, Field, Index, Relationship


class ArticleBase(SQLModel):
    title: str = Field(index=True)  # Index for faster searching
    perex: str  # Article summary/excerpt
    source: str = Field(index=True)  # News website name
    url: str = Field(index=True)  # URL should be unique (removed unique constraint temporarily)
    title_hash: str = Field(default="", index=True)  # Hash of normalized title for duplicate detection
    scraped_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)  # Track updates
    


    

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


# New models for NLP features
class EntityBase(SQLModel):
    text: str = Field(index=True)
    entity_type: str = Field(index=True)  # PERSON, ORG, GPE, MISC
    confidence: float = Field(default=0.0)
    

class Entity(EntityBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Relationships
    article_entities: List["ArticleEntity"] = Relationship(back_populates="entity")


class ArticleEntity(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    article_id: int = Field(foreign_key="article.id", index=True)
    entity_id: int = Field(foreign_key="entity.id", index=True)
    position_start: int = Field(default=0)  # Character position in text
    position_end: int = Field(default=0)
    
    # Relationships
    article: "Article" = Relationship()
    entity: Entity = Relationship(back_populates="article_entities")


class TopicBase(SQLModel):
    name: str = Field(index=True)
    keywords: str = Field(default="")  # JSON array of keywords
    

class Topic(TopicBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Relationships
    article_topics: List["ArticleTopic"] = Relationship(back_populates="topic")


class ArticleTopic(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    article_id: int = Field(foreign_key="article.id", index=True)
    topic_id: int = Field(foreign_key="topic.id", index=True)
    relevance_score: float = Field(default=0.0)
    
    # Relationships
    article: "Article" = Relationship()
    topic: Topic = Relationship(back_populates="article_topics")


class SentimentAnalysis(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    article_id: int = Field(foreign_key="article.id", unique=True, index=True)
    
    # Sentiment scores
    sentiment_label: str = Field(index=True)  # positive, negative, neutral
    sentiment_score: float = Field(default=0.0)  # -1 to 1
    
    # Emotional analysis
    emotion_scores: str = Field(default="{}")  # JSON with emotion scores
    
    # Text properties
    subjectivity: float = Field(default=0.0)  # 0 (objective) to 1 (subjective)
    
    # Relationships
    article: "Article" = Relationship()


# Updated Article model with relationships
class Article(ArticleBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # NLP processing status
    nlp_processed: bool = Field(default=False, index=True)
    nlp_processed_at: Optional[datetime] = Field(default=None)
    
    # Ensure we have indexes for common queries
    __table_args__ = (
        Index("idx_source_scraped", "source", "scraped_at"),
        Index("idx_title_hash_source", "title_hash", "source"),
        Index("idx_nlp_processed", "nlp_processed"),
    )
    
    # Relationships to NLP data
    sentiment: Optional[SentimentAnalysis] = Relationship()
    article_entities: List[ArticleEntity] = Relationship(back_populates="article")
    article_topics: List[ArticleTopic] = Relationship(back_populates="article")