from typing import List
from bs4 import BeautifulSoup
from .....core.models import ArticleCreate
from .....core.logging_handler import get_logger
from ..base import BaseScraper

logger = get_logger(__name__)


class DenikScraper(BaseScraper):
    """Scraper for denik.cz news website (major regional news network)."""
    
    def __init__(self):
        super().__init__("denik", "https://www.denik.cz")
    
    async def extract_articles(self, soup: BeautifulSoup, page) -> List[ArticleCreate]:
        """Extract articles from denik.cz with regional news specific selectors."""
        articles = []
        
        # Deník has extensive regional content with dynamic loading
        await self.scroll_page(page, max_scrolls=5)
        
        # Get updated content after scrolling
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Deník specific selectors - regional news structure
        article_selectors = [
            # Primary containers
            'article',
            '.article',
            '.story',
            '.news-item',
            '.item',
            # Deník specific classes
            '.article-item',
            '.story-item',
            '.news-story',
            '.content-item',
            '.feed-item',
            '.listing-item',
            '.teaser',
            '.article-teaser',
            '.story-teaser',
            '.article-card',
            '.news-card',
            '.story-card',
            '.content-card',
            # Regional news specific
            '.regional-article',
            '.regional-news',
            '.local-news',
            '.regional-item',
            # Generic selectors
            '[class*="article"]',
            '[class*="story"]',
            '[class*="item"]',
            '[class*="teaser"]',
            '[class*="card"]',
            '[class*="news"]',
            '.entry',
            '.post',
            # Data attributes
            '[data-article]',
            '[data-story]',
            '[data-item]',
            '[data-news]'
        ]
        
        elements = self.find_article_elements(soup, article_selectors)
        logger.info(f"Found {len(elements)} potential article elements on Deník.cz")
        
        for element in elements[:80]:  # Process up to 80 articles for Deník
            try:
                # Enhanced title extraction for Deník.cz
                title_selectors = [
                    # Headlines with links
                    'h1 a', 'h2 a', 'h3 a', 'h4 a', 'h5 a',
                    # Direct headlines
                    'h1', 'h2', 'h3', 'h4', 'h5',
                    # Common class-based selectors
                    '.title a', '.headline a', '.title', '.headline',
                    '.article-title a', '.article-title',
                    '.story-title a', '.story-title',
                    '.entry-title a', '.entry-title',
                    '.teaser-title a', '.teaser-title',
                    '.card-title a', '.card-title',
                    '.news-title a', '.news-title',
                    # Deník specific URL patterns
                    'a[href*="/clanek/"]', 'a[href*="/zpravy/"]',
                    'a[href*="/regiony/"]', 'a[href*="/kraje/"]',
                    'a[href*="/ekonomika/"]', 'a[href*="/kultura/"]',
                    'a[href*="/sport/"]', 'a[href*="/zahranici/"]',
                    'a[href*="/domaci/"]', 'a[href*="/politika/"]',
                    'a[href*="/lifestyle/"]', 'a[href*="/auto/"]',
                    # Class-based title selectors
                    'a.title', 'a.headline', 'a.article-link',
                    'a.story-link', 'a.teaser-link', 'a.card-link',
                    # Fallback selectors
                    'a[title]', '.link-title'
                ]
                
                title = self.extract_title_from_element(element, title_selectors)
                if not title:
                    continue
                
                # Extract perex/summary with Deník-specific selectors
                perex_selectors = [
                    '.perex', '.summary', '.excerpt', '.abstract', '.description',
                    '.article-perex', '.story-perex', '.teaser-perex',
                    '.article-summary', '.story-summary', '.teaser-summary',
                    '.content-summary', '.article-description',
                    '.teaser-description', '.item-description',
                    '.card-description', '.card-summary',
                    '.news-description', '.news-summary',
                    'p.perex', 'p.summary', 'p.excerpt', 'p.description',
                    'p', '.content p', '.lead', '.intro', '.deck'
                ]
                
                perex = self.extract_perex_from_element(element, perex_selectors)
                
                # Extract URL with Deník-specific selectors
                url_selectors = [
                    # Title links
                    'h1 a', 'h2 a', 'h3 a', 'h4 a', 'h5 a',
                    '.title a', '.headline a', '.article-title a',
                    '.story-title a', '.entry-title a', '.teaser-title a',
                    '.card-title a', '.news-title a',
                    # Deník specific URL patterns
                    'a[href*="/clanek/"]', 'a[href*="/zpravy/"]',
                    'a[href*="/regiony/"]', 'a[href*="/kraje/"]',
                    'a[href*="/ekonomika/"]', 'a[href*="/kultura/"]',
                    'a[href*="/sport/"]', 'a[href*="/zahranici/"]',
                    'a[href*="/domaci/"]', 'a[href*="/politika/"]',
                    'a[href*="/lifestyle/"]', 'a[href*="/auto/"]',
                    # Generic link selectors
                    'a.article-link', 'a.story-link', 'a.teaser-link',
                    'a.item-link', 'a.content-link', 'a.card-link',
                    'a[href]'
                ]
                
                url = self.extract_url_from_element(element, url_selectors)
                if not url:
                    continue
                
                # Create article with validation
                article = self.create_article(title, perex, url)
                if article:
                    articles.append(article)
                    logger.debug(f"Extracted article: {title[:50]}...")
                    
            except Exception as e:
                self.logger.warning(f"Error parsing article element: {e}")
                continue
        
        logger.info(f"Successfully extracted {len(articles)} articles from Deník.cz")
        return articles


# Factory function for backward compatibility
async def scrape_denik() -> List[ArticleCreate]:
    """Factory function to maintain backward compatibility."""
    scraper = DenikScraper()
    return await scraper.scrape()