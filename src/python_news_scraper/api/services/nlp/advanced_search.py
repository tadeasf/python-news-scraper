"""
Advanced search service with SQLite FTS5 trigram support for fuzzy and diacritic-insensitive search.
"""

import sqlite3
from typing import List, Dict, Optional, Tuple
import json
import re
from loguru import logger
from unidecode import unidecode

from ....core.database import get_database_url


class AdvancedSearchService:
    """Advanced search using SQLite FTS5 with trigram tokenizer for fuzzy search."""
    
    def __init__(self):
        self.db_path = get_database_url().replace("sqlite:///", "")
        
    async def initialize_fts_tables(self):
        """Initialize FTS5 tables for advanced search."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create FTS5 table for articles with trigram tokenizer
                cursor.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
                        article_id UNINDEXED,
                        title,
                        perex,
                        source UNINDEXED,
                        normalized_title,
                        normalized_perex,
                        tokenize='trigram case_sensitive 0 remove_diacritics 1',
                        detail='none'
                    )
                """)
                
                # Create FTS5 table for entities
                cursor.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts USING fts5(
                        entity_id UNINDEXED,
                        text,
                        entity_type UNINDEXED,
                        normalized_text,
                        tokenize='trigram case_sensitive 0 remove_diacritics 1'
                    )
                """)
                
                # Create FTS5 table for topics
                cursor.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS topics_fts USING fts5(
                        topic_id UNINDEXED,
                        name,
                        keywords,
                        normalized_name,
                        tokenize='trigram case_sensitive 0 remove_diacritics 1'
                    )
                """)
                
                conn.commit()
                logger.info("FTS5 tables initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize FTS5 tables: {e}")
            raise
    
    def normalize_for_search(self, text: str) -> str:
        """Normalize text for diacritic-insensitive search."""
        if not text:
            return ""
        # Remove diacritics and convert to lowercase
        normalized = unidecode(text.lower())
        # Clean up extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized
    
    async def index_article(self, article_id: int, title: str, perex: str, source: str):
        """Add or update an article in the FTS index."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Delete existing entry if it exists
                cursor.execute("DELETE FROM articles_fts WHERE article_id = ?", (article_id,))
                
                # Insert new entry
                cursor.execute("""
                    INSERT INTO articles_fts (
                        article_id, title, perex, source, 
                        normalized_title, normalized_perex
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    article_id, title, perex, source,
                    self.normalize_for_search(title),
                    self.normalize_for_search(perex)
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to index article {article_id}: {e}")
    
    async def index_entity(self, entity_id: int, text: str, entity_type: str):
        """Add or update an entity in the FTS index."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Delete existing entry if it exists
                cursor.execute("DELETE FROM entities_fts WHERE entity_id = ?", (entity_id,))
                
                # Insert new entry
                cursor.execute("""
                    INSERT INTO entities_fts (
                        entity_id, text, entity_type, normalized_text
                    ) VALUES (?, ?, ?, ?)
                """, (
                    entity_id, text, entity_type,
                    self.normalize_for_search(text)
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to index entity {entity_id}: {e}")
    
    async def index_topic(self, topic_id: int, name: str, keywords: str):
        """Add or update a topic in the FTS index."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Delete existing entry if it exists
                cursor.execute("DELETE FROM topics_fts WHERE topic_id = ?", (topic_id,))
                
                # Insert new entry
                cursor.execute("""
                    INSERT INTO topics_fts (
                        topic_id, name, keywords, normalized_name
                    ) VALUES (?, ?, ?, ?)
                """, (
                    topic_id, name, keywords,
                    self.normalize_for_search(name)
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to index topic {topic_id}: {e}")
    
    async def search_articles(
        self, 
        query: str, 
        source_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """Search articles with fuzzy matching and diacritic insensitivity."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Normalize query for better matching
                normalized_query = self.normalize_for_search(query)
                
                # Build the search query
                base_query = """
                    SELECT 
                        a.id,
                        a.title,
                        a.perex,
                        a.source,
                        a.url,
                        a.scraped_at,
                        bm25(articles_fts) as relevance_score
                    FROM articles_fts
                    JOIN article a ON a.id = articles_fts.article_id
                    WHERE articles_fts MATCH ?
                """
                
                params = [f'"{normalized_query}" OR "{query}"']
                
                if source_filter:
                    base_query += " AND a.source = ?"
                    params.append(source_filter)
                
                base_query += " ORDER BY relevance_score DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                
                cursor.execute(base_query, params)
                results = cursor.fetchall()
                
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error(f"Article search failed: {e}")
            return []
    
    async def search_entities(
        self, 
        query: str,
        entity_type: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """Search entities with fuzzy matching."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                normalized_query = self.normalize_for_search(query)
                
                base_query = """
                    SELECT 
                        e.id,
                        e.text,
                        e.entity_type,
                        e.confidence,
                        COUNT(ae.article_id) as article_count,
                        bm25(entities_fts) as relevance_score
                    FROM entities_fts
                    JOIN entity e ON e.id = entities_fts.entity_id
                    LEFT JOIN articleentity ae ON ae.entity_id = e.id
                    WHERE entities_fts MATCH ?
                """
                
                params = [f'"{normalized_query}" OR "{query}"']
                
                if entity_type:
                    base_query += " AND e.entity_type = ?"
                    params.append(entity_type)
                
                base_query += """
                    GROUP BY e.id
                    ORDER BY relevance_score DESC 
                    LIMIT ?
                """
                params.append(limit)
                
                cursor.execute(base_query, params)
                results = cursor.fetchall()
                
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error(f"Entity search failed: {e}")
            return []
    
    async def search_topics(self, query: str, limit: int = 10) -> List[Dict]:
        """Search topics with fuzzy matching."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                normalized_query = self.normalize_for_search(query)
                
                cursor.execute("""
                    SELECT 
                        t.id,
                        t.name,
                        t.keywords,
                        COUNT(at.article_id) as article_count,
                        bm25(topics_fts) as relevance_score
                    FROM topics_fts
                    JOIN topic t ON t.id = topics_fts.topic_id
                    LEFT JOIN articletopic at ON at.topic_id = t.id
                    WHERE topics_fts MATCH ?
                    GROUP BY t.id
                    ORDER BY relevance_score DESC 
                    LIMIT ?
                """, [f'"{normalized_query}" OR "{query}"', limit])
                
                results = cursor.fetchall()
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error(f"Topic search failed: {e}")
            return []
    
    async def get_search_suggestions(self, partial_query: str, limit: int = 5) -> List[str]:
        """Get search suggestions based on partial query."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                normalized_query = self.normalize_for_search(partial_query)
                suggestions = set()
                
                # Get suggestions from article titles
                cursor.execute("""
                    SELECT title FROM articles_fts 
                    WHERE articles_fts MATCH ? 
                    LIMIT ?
                """, [f'{normalized_query}*', limit])
                
                for row in cursor.fetchall():
                    # Extract relevant words from title
                    words = row['title'].lower().split()
                    for word in words:
                        if normalized_query in self.normalize_for_search(word):
                            suggestions.add(word)
                
                # Get suggestions from entities
                cursor.execute("""
                    SELECT text FROM entities_fts 
                    WHERE entities_fts MATCH ? 
                    LIMIT ?
                """, [f'{normalized_query}*', limit])
                
                for row in cursor.fetchall():
                    if normalized_query in self.normalize_for_search(row['text']):
                        suggestions.add(row['text'])
                
                return list(suggestions)[:limit]
                
        except Exception as e:
            logger.error(f"Search suggestions failed: {e}")
            return []
    
    async def analyze_source_coverage(self, topic: str) -> Dict[str, Dict]:
        """Analyze how different sources cover a specific topic."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                normalized_topic = self.normalize_for_search(topic)
                
                # Get articles related to the topic
                cursor.execute("""
                    SELECT 
                        a.source,
                        COUNT(*) as article_count,
                        AVG(sa.sentiment_score) as avg_sentiment,
                        sa.sentiment_label,
                        COUNT(CASE WHEN sa.sentiment_label = 'positive' THEN 1 END) as positive_count,
                        COUNT(CASE WHEN sa.sentiment_label = 'negative' THEN 1 END) as negative_count,
                        COUNT(CASE WHEN sa.sentiment_label = 'neutral' THEN 1 END) as neutral_count
                    FROM articles_fts
                    JOIN article a ON a.id = articles_fts.article_id
                    LEFT JOIN sentimentanalysis sa ON sa.article_id = a.id
                    WHERE articles_fts MATCH ?
                    GROUP BY a.source
                    ORDER BY article_count DESC
                """, [f'"{normalized_topic}" OR "{topic}"'])
                
                results = cursor.fetchall()
                
                source_analysis = {}
                for row in results:
                    source_analysis[row['source']] = {
                        'article_count': row['article_count'],
                        'avg_sentiment': row['avg_sentiment'] or 0.0,
                        'sentiment_distribution': {
                            'positive': row['positive_count'] or 0,
                            'negative': row['negative_count'] or 0,
                            'neutral': row['neutral_count'] or 0
                        }
                    }
                
                return source_analysis
                
        except Exception as e:
            logger.error(f"Source coverage analysis failed: {e}")
            return {}


# Global instance
advanced_search = AdvancedSearchService()