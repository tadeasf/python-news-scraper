"""
Main NLP service that orchestrates all NLP processing for articles.
"""

import json
from datetime import datetime
from typing import List, Dict, Optional
from sqlmodel import Session, select

from loguru import logger

from ....core.database import get_session
from ....core.models import (
    Article, Entity, ArticleEntity, Topic, ArticleTopic, 
    SentimentAnalysis, EntityBase, TopicBase
)
from .czech_nlp import czech_nlp
from .advanced_search import advanced_search


class NLPProcessingService:
    """Service for processing articles with NLP analysis."""
    
    def __init__(self):
        self.czech_nlp = czech_nlp
        self.search_service = advanced_search
        self._initialized = False
    
    async def initialize(self):
        """Initialize the NLP service and all its components."""
        if self._initialized:
            return
            
        logger.info("Initializing NLP Processing Service...")
        
        # Initialize the Czech NLP pipeline
        await self.czech_nlp.initialize()
        
        # Initialize FTS tables
        await self.search_service.initialize_fts_tables()
        
        self._initialized = True
        logger.info("NLP Processing Service initialized successfully")
    
    async def process_article(self, article_id: int) -> bool:
        """Process a single article with full NLP analysis."""
        if not self._initialized:
            await self.initialize()
            
        try:
            with get_session() as session:
                # Get the article
                article = session.get(Article, article_id)
                if not article:
                    logger.error(f"Article {article_id} not found")
                    return False
                
                if article.nlp_processed:
                    logger.info(f"Article {article_id} already processed")
                    return True
                
                logger.info(f"Processing article {article_id}: {article.title[:50]}...")
                
                # Combine title and perex for analysis
                full_text = f"{article.title}\n\n{article.perex}"
                
                # 1. Extract entities
                await self._process_entities(session, article, full_text)
                
                # 2. Analyze sentiment
                await self._process_sentiment(session, article, full_text)
                
                # 3. Index in FTS
                await self.search_service.index_article(
                    article_id, article.title, article.perex, article.source
                )
                
                # 4. Mark as processed
                article.nlp_processed = True
                article.nlp_processed_at = datetime.utcnow()
                session.add(article)
                session.commit()
                
                logger.info(f"Successfully processed article {article_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to process article {article_id}: {e}")
            return False
    
    async def _process_entities(self, session: Session, article: Article, text: str):
        """Extract and store entities for an article."""
        try:
            entities_data = self.czech_nlp.extract_entities(text)
            
            for entity_data in entities_data:
                # Find or create entity
                entity = self._find_or_create_entity(
                    session, 
                    entity_data['text'], 
                    entity_data['label'],
                    entity_data.get('confidence', 0.8)
                )
                
                # Create article-entity relationship
                article_entity = ArticleEntity(
                    article_id=article.id,
                    entity_id=entity.id,
                    position_start=entity_data.get('start', 0),
                    position_end=entity_data.get('end', 0)
                )
                session.add(article_entity)
                
                # Index entity in FTS
                await self.search_service.index_entity(
                    entity.id, entity.text, entity.entity_type
                )
                
            session.commit()
            
        except Exception as e:
            logger.error(f"Entity processing failed: {e}")
    
    def _find_or_create_entity(self, session: Session, text: str, entity_type: str, confidence: float) -> Entity:
        """Find existing entity or create new one."""
        # Normalize text for comparison
        normalized_text = text.lower().strip()
        
        # Look for existing entity
        statement = select(Entity).where(
            Entity.text.ilike(f"%{normalized_text}%"),
            Entity.entity_type == entity_type
        )
        existing_entity = session.exec(statement).first()
        
        if existing_entity:
            # Update confidence if this one is higher
            if confidence > existing_entity.confidence:
                existing_entity.confidence = confidence
                session.add(existing_entity)
            return existing_entity
        
        # Create new entity
        entity = Entity(
            text=text,
            entity_type=entity_type,
            confidence=confidence
        )
        session.add(entity)
        session.flush()  # Get the ID
        return entity
    
    async def _process_sentiment(self, session: Session, article: Article, text: str):
        """Analyze and store sentiment for an article."""
        try:
            sentiment_data = self.czech_nlp.analyze_sentiment(text)
            
            # Delete existing sentiment analysis if any
            existing_sentiment = session.exec(
                select(SentimentAnalysis).where(SentimentAnalysis.article_id == article.id)
            ).first()
            
            if existing_sentiment:
                session.delete(existing_sentiment)
            
            # Create new sentiment analysis
            sentiment = SentimentAnalysis(
                article_id=article.id,
                sentiment_label=sentiment_data['sentiment_label'],
                sentiment_score=sentiment_data['sentiment_score'],
                emotion_scores=json.dumps(sentiment_data['emotion_scores']),
                subjectivity=sentiment_data['subjectivity']
            )
            session.add(sentiment)
            session.commit()
            
        except Exception as e:
            logger.error(f"Sentiment processing failed: {e}")
    
    async def process_topics_batch(self, limit: int = 100) -> bool:
        """Process topics for a batch of articles using LDA/clustering."""
        if not self._initialized:
            await self.initialize()
            
        try:
            with get_session() as session:
                # Get unprocessed articles
                statement = select(Article).where(Article.nlp_processed == True).limit(limit)
                articles = session.exec(statement).all()
                
                if len(articles) < 2:
                    logger.info("Not enough articles for topic modeling")
                    return True
                
                # Prepare texts for topic modeling
                texts = []
                article_ids = []
                for article in articles:
                    texts.append(f"{article.title}\n{article.perex}")
                    article_ids.append(article.id)
                
                # Discover topics
                topic_data = self.czech_nlp.discover_topics(texts, n_topics=min(10, len(texts) // 5))
                
                if not topic_data['topics']:
                    logger.warning("No topics discovered")
                    return True
                
                # Store topics
                topic_map = {}
                for topic_info in topic_data['topics']:
                    topic = self._find_or_create_topic(
                        session, 
                        topic_info['name'], 
                        topic_info['keywords']
                    )
                    topic_map[topic_info['id']] = topic
                    
                    # Index topic in FTS
                    await self.search_service.index_topic(
                        topic.id, topic.name, topic.keywords
                    )
                
                # Create article-topic relationships
                for doc_topic in topic_data['document_topics']:
                    article_id = article_ids[doc_topic['document_id']]
                    topic = topic_map[doc_topic['topic_id']]
                    
                    # Check if relationship already exists
                    existing = session.exec(
                        select(ArticleTopic).where(
                            ArticleTopic.article_id == article_id,
                            ArticleTopic.topic_id == topic.id
                        )
                    ).first()
                    
                    if not existing:
                        article_topic = ArticleTopic(
                            article_id=article_id,
                            topic_id=topic.id,
                            relevance_score=doc_topic['relevance_score']
                        )
                        session.add(article_topic)
                
                session.commit()
                logger.info(f"Processed topics for {len(articles)} articles")
                return True
                
        except Exception as e:
            logger.error(f"Topic processing failed: {e}")
            return False
    
    def _find_or_create_topic(self, session: Session, name: str, keywords: List[str]) -> Topic:
        """Find existing topic or create new one."""
        keywords_str = json.dumps(keywords)
        
        # Look for existing topic with similar keywords
        statement = select(Topic).where(Topic.name == name)
        existing_topic = session.exec(statement).first()
        
        if existing_topic:
            # Update keywords if different
            if existing_topic.keywords != keywords_str:
                existing_topic.keywords = keywords_str
                session.add(existing_topic)
            return existing_topic
        
        # Create new topic
        topic = Topic(
            name=name,
            keywords=keywords_str
        )
        session.add(topic)
        session.flush()  # Get the ID
        return topic
    
    async def reindex_all_articles(self):
        """Reindex all articles in the FTS search."""
        try:
            with get_session() as session:
                statement = select(Article)
                articles = session.exec(statement).all()
                
                for article in articles:
                    await self.search_service.index_article(
                        article.id, article.title, article.perex, article.source
                    )
                
                logger.info(f"Reindexed {len(articles)} articles")
                
        except Exception as e:
            logger.error(f"Reindexing failed: {e}")
    
    async def get_processing_stats(self) -> Dict:
        """Get statistics about NLP processing."""
        try:
            with get_session() as session:
                total_articles = session.exec(select(Article)).all()
                processed_articles = session.exec(
                    select(Article).where(Article.nlp_processed == True)
                ).all()
                
                total_entities = session.exec(select(Entity)).all()
                total_topics = session.exec(select(Topic)).all()
                
                return {
                    "total_articles": len(total_articles),
                    "processed_articles": len(processed_articles),
                    "processing_percentage": len(processed_articles) / len(total_articles) * 100 if total_articles else 0,
                    "total_entities": len(total_entities),
                    "total_topics": len(total_topics),
                    "unprocessed_articles": len(total_articles) - len(processed_articles)
                }
                
        except Exception as e:
            logger.error(f"Failed to get processing stats: {e}")
            return {}


# Global instance
nlp_service = NLPProcessingService()