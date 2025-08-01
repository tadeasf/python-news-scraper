import asyncio
from datetime import datetime
from typing import List, Dict, Any
from sqlmodel import Session, select, or_
from ...core.database import get_session, engine
from ...core.models import Article, ArticleCreate, ArticleBase
from ...core.logging_handler import get_logger, async_catch
from .scraping.modules.aktualne import AktualneScraper, scrape_aktualne
from .scraping.modules.novinky import NovinkyScraper, scrape_novinky  
from .scraping.modules.idnes import IdnesScraper, scrape_idnes
from .scraping.modules.ihned import IhnedScraper, scrape_ihned
from .scraping.modules.seznamzpravy import SeznamZpravyScraper, scrape_seznamzpravy
from .scraping.modules.blesk import BleskScraper, scrape_blesk
from .scraping.modules.ct24 import CT24Scraper, scrape_ct24
from .scraping.modules.irozhlas import IRozhlasScraper, scrape_irozhlas
from .scraping.modules.lidovky import LidovkyScraper, scrape_lidovky
from .scraping.modules.denik import DenikScraper, scrape_denik
from .scraping.modules.forum24 import Forum24Scraper, scrape_forum24
from .scraping.modules.e15 import E15Scraper, scrape_e15

logger = get_logger(__name__)


class ScrapingService:
    def __init__(self):
        # Use the new OOP scrapers
        self.scrapers = {
            'aktualne': AktualneScraper(),
            'novinky': NovinkyScraper(),
            'idnes': IdnesScraper(),
            'ihned': IhnedScraper(),
            'seznamzpravy': SeznamZpravyScraper(),
            'blesk': BleskScraper(),
            'ct24': CT24Scraper(),
            'irozhlas': IRozhlasScraper(),
            'lidovky': LidovkyScraper(),
            'denik': DenikScraper(),
            'forum24': Forum24Scraper(),
            'e15': E15Scraper(),
        }
        
        # Keep backward compatibility functions
        self.scraper_functions = {
            'aktualne': scrape_aktualne,
            'novinky': scrape_novinky,
            'idnes': scrape_idnes,
            'ihned': scrape_ihned,
            'seznamzpravy': scrape_seznamzpravy,
            'blesk': scrape_blesk,
            'ct24': scrape_ct24,
            'irozhlas': scrape_irozhlas,
            'lidovky': scrape_lidovky,
            'denik': scrape_denik,
            'forum24': scrape_forum24,
            'e15': scrape_e15,
        }

    async def scrape_all_sources_concurrent(self) -> int:
        """Scrape all news sources concurrently for better performance."""
        logger.info("Starting concurrent scraping of all sources")
        
        # Create tasks for all scrapers to run concurrently
        tasks = []
        for source_name, scraper in self.scrapers.items():
            task = asyncio.create_task(
                self._scrape_source_with_error_handling(source_name, scraper),
                name=f"scrape_{source_name}"
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        total_saved = 0
        for i, result in enumerate(results):
            source_name = list(self.scrapers.keys())[i]
            if isinstance(result, Exception):
                logger.error(f"Error scraping {source_name}: {result}")
            else:
                saved_count = result
                total_saved += saved_count
                logger.info(f"Saved {saved_count} new articles from {source_name}")
        
        logger.info(f"Concurrent scraping complete. Total new articles saved: {total_saved}")
        return total_saved

    async def _scrape_source_with_error_handling(self, source_name: str, scraper) -> int:
        """Scrape a single source with error handling."""
        try:
            logger.info(f"Starting scrape for {source_name}")
            articles = await scraper.scrape()
            saved_count = await self._save_articles(articles)
            return saved_count
        except Exception as e:
            logger.error(f"Error scraping {source_name}: {e}")
            return 0

    async def scrape_all_sources(self) -> int:
        """Scrape all news sources (uses concurrent scraping for better performance)."""
        return await self.scrape_all_sources_concurrent()

    async def scrape_source(self, source: str) -> int:
        """Scrape a specific news source."""
        if source not in self.scrapers:
            raise ValueError(f"Unknown source: {source}")
        
        try:
            logger.info(f"Starting scrape for {source}")
            scraper = self.scrapers[source]
            articles = await scraper.scrape()
            saved_count = await self._save_articles(articles)
            logger.info(f"Saved {saved_count} new articles from {source}")
            return saved_count
        except Exception as e:
            logger.error(f"Error scraping {source}: {e}")
            raise

    @async_catch(reraise=False)
    async def _save_articles(self, articles: List[ArticleCreate]) -> int:
        """
        Save articles to database with intelligent duplicate handling.
        Updates existing articles if found by URL or similar title.
        """
        if not articles:
            return 0
        
        saved_count = 0
        updated_count = 0
        
        with Session(engine) as session:
            for article_data in articles:
                try:
                    # Convert to ArticleBase with computed fields
                    article_base = article_data.to_article_base()
                    
                    # Check for existing article by URL (exact match)
                    existing_by_url = session.exec(
                        select(Article).where(Article.url == article_base.url)
                    ).first()
                    
                    if existing_by_url:
                        # Update existing article with new information
                        existing_by_url.title = article_base.title
                        existing_by_url.perex = article_base.perex
                        existing_by_url.title_hash = article_base.title_hash
                        existing_by_url.updated_at = datetime.utcnow()
                        updated_count += 1
                        logger.debug(f"Updated existing article: {article_base.title[:50]}...")
                        continue
                    
                    # Check for similar title (duplicate detection)
                    existing_by_title = session.exec(
                        select(Article).where(
                            Article.title_hash == article_base.title_hash,
                            Article.source == article_base.source
                        )
                    ).first()
                    
                    if existing_by_title:
                        # Update with newer URL if different
                        if existing_by_title.url != article_base.url:
                            existing_by_title.url = article_base.url
                            existing_by_title.perex = article_base.perex
                            existing_by_title.updated_at = datetime.utcnow()
                            updated_count += 1
                            logger.debug(f"Updated article URL: {article_base.title[:50]}...")
                        else:
                            logger.debug(f"Duplicate article (same title): {article_base.title[:50]}...")
                        continue
                    
                    # Create new article
                    article = Article.model_validate(article_base.model_dump())
                    session.add(article)
                    saved_count += 1
                    logger.debug(f"Added new article: {article_base.title[:50]}...")
                    
                except Exception as e:
                    logger.warning(f"Error processing article {article_data.title[:50]}...: {e}")
                    continue
            
            try:
                session.commit()
                if saved_count > 0 or updated_count > 0:
                    logger.info(f"Database operation successful: {saved_count} new, {updated_count} updated articles")
            except Exception as e:
                logger.error(f"Error committing articles to database: {e}")
                session.rollback()
                saved_count = 0
        
        return saved_count


# Global instance
scraping_service = ScrapingService()