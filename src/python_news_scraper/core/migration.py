"""
Database migration utilities for Czech News Scraper.
Handles schema updates when models change.
"""

import sqlite3
from pathlib import Path
from typing import List
import logging

logger = logging.getLogger(__name__)


class DatabaseMigration:
    """Handles database schema migrations."""
    
    def __init__(self, db_path: str = "news_scraper.db"):
        self.db_path = db_path
        self.migrations_applied = []
    
    def get_current_schema(self) -> List[str]:
        """Get current table schemas."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='article'")
            result = cursor.fetchone()
            return [result[0]] if result else []
    
    def column_exists(self, table_name: str, column_name: str) -> bool:
        """Check if a column exists in a table."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [row[1] for row in cursor.fetchall()]
            return column_name in columns
    
    def add_column_if_not_exists(self, table_name: str, column_name: str, column_definition: str):
        """Add a column to a table if it doesn't exist."""
        if not self.column_exists(table_name, column_name):
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
                cursor.execute(sql)
                conn.commit()
                logger.info(f"Added column {column_name} to table {table_name}")
                return True
        else:
            logger.debug(f"Column {column_name} already exists in table {table_name}")
            return False
    
    def create_index_if_not_exists(self, index_name: str, table_name: str, columns: str):
        """Create an index if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name=?
            """, (index_name,))
            
            if not cursor.fetchone():
                sql = f"CREATE INDEX {index_name} ON {table_name} ({columns})"
                cursor.execute(sql)
                conn.commit()
                logger.info(f"Created index {index_name}")
                return True
            else:
                logger.debug(f"Index {index_name} already exists")
                return False
    
    def migrate_to_v2(self):
        """Migrate to version 2 schema with new fields."""
        logger.info("Starting migration to schema v2...")
        
        # Add new columns
        changes_made = False
        
        # Add title_hash column
        if self.add_column_if_not_exists('article', 'title_hash', 'VARCHAR'):
            changes_made = True
        
        # Add updated_at column
        if self.add_column_if_not_exists('article', 'updated_at', 'DATETIME'):
            changes_made = True
        
        # Create indexes for better performance
        if self.create_index_if_not_exists('idx_article_title_hash', 'article', 'title_hash'):
            changes_made = True
        
        if self.create_index_if_not_exists('idx_article_source', 'article', 'source'):
            changes_made = True
        
        if self.create_index_if_not_exists('idx_article_scraped_at', 'article', 'scraped_at'):
            changes_made = True
        
        # Update existing records with missing data
        self.populate_missing_fields()
        
        if changes_made:
            logger.info("Migration to schema v2 completed successfully")
        else:
            logger.info("Schema v2 migration not needed - already up to date")
    
    def populate_missing_fields(self):
        """Populate missing fields in existing records."""
        import hashlib
        import re
        from datetime import datetime
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get records with missing title_hash
            cursor.execute("""
                SELECT id, title FROM article 
                WHERE title_hash IS NULL OR title_hash = ''
            """)
            
            records_to_update = cursor.fetchall()
            
            if records_to_update:
                logger.info(f"Updating {len(records_to_update)} records with missing title_hash")
                
                for record_id, title in records_to_update:
                    if title:
                        # Normalize title for hashing
                        normalized_title = title.lower().strip()
                        normalized_title = re.sub(r'[^\w\s]', '', normalized_title)
                        normalized_title = re.sub(r'\s+', ' ', normalized_title)
                        
                        # Create hash
                        title_hash = hashlib.md5(normalized_title.encode('utf-8')).hexdigest()
                        
                        # Update record
                        cursor.execute("""
                            UPDATE article 
                            SET title_hash = ?, updated_at = ?
                            WHERE id = ?
                        """, (title_hash, datetime.utcnow().isoformat(), record_id))
                
                conn.commit()
                logger.info("Successfully updated existing records")
    
    def run_all_migrations(self):
        """Run all necessary migrations."""
        logger.info("Starting database migrations...")
        
        # Check if database file exists
        if not Path(self.db_path).exists():
            logger.info("Database file doesn't exist yet - will be created by SQLModel")
            return
        
        # Run migrations
        self.migrate_to_v2()
        
        logger.info("All migrations completed")


# Global migration instance
migration = DatabaseMigration()

def run_migrations():
    """Run all database migrations."""
    migration.run_all_migrations()