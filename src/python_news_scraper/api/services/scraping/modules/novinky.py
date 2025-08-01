from typing import List
from bs4 import BeautifulSoup
from .....core.models import ArticleCreate
from .....core.logging_handler import get_logger
from ..base import BaseScraper

logger = get_logger(__name__)


class NovinkyScraper(BaseScraper):
    """Scraper for novinky.cz news website."""
    
    def __init__(self):
        super().__init__("novinky", "https://novinky.cz")
    
    async def extract_articles(self, soup: BeautifulSoup, page) -> List[ArticleCreate]:
        """Extract articles from novinky.cz with enhanced selectors."""
        articles = []
        
        # Scroll to load more content - novinky.cz has dynamic loading
        await self.scroll_page(page, max_scrolls=5)
        
        # Get updated content after scrolling
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Enhanced selectors for novinky.cz
        article_selectors = [
            # Primary containers
            'article',
            '.article',
            '.story',
            '.news-item',
            '.item',
            '.clanek',
            # novinky.cz specific classes
            '.clanek-nahled',
            '.article-preview',
            '.news-preview',
            '.story-preview',
            '.content-article',
            '.listing-article',
            # Generic selectors
            '[class*="article"]',
            '[class*="story"]',
            '[class*="item"]',
            '[class*="clanek"]',
            '.content-box',
            '.listing-item',
            '.news-box',
            # Additional selectors
            '.teaser',
            '.feed-item',
            '[data-article]',
            '.entry',
            '.post'
        ]
        
        elements = self.find_article_elements(soup, article_selectors)
        
        logger.info(f"Found {len(elements)} potential article elements on novinky.cz")
        
        for element in elements[:80]:  # Process up to 80 articles
            try:
                # Enhanced title extraction for novinky.cz
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
                    '.clanek-title a', '.clanek-title',
                    # novinky.cz specific URL patterns
                    'a[href*="/clanek/"]', 'a[href*="/zpravy/"]',
                    'a[href*="/sport/"]', 'a[href*="/ekonomika/"]',
                    'a[href*="/kultura/"]', 'a[href*="/zahranici/"]',
                    # Class-based title selectors
                    'a.title', 'a.headline', 'a.clanek-link',
                    # Fallback selectors
                    'a[title]', '.link-title', '.news-title'
                ]
                
                title = self.extract_title_from_element(element, title_selectors)
                if not title:
                    continue
                
                # Extract perex/summary
                perex_selectors = [
                    '.perex',
                    '.summary',
                    '.excerpt',
                    '.abstract',
                    '.description',
                    '.clanek-perex',
                    'p.perex',
                    'p',
                    '.content p'
                ]
                
                perex = self.extract_perex_from_element(element, perex_selectors)
                
                # Extract URL
                url_selectors = [
                    'h1 a',
                    'h2 a',
                    'h3 a',
                    'h4 a',
                    '.title a',
                    '.headline a',
                    'a[href*="/clanek/"]',
                    'a.title',
                    'a.headline',
                    'a[href]'
                ]
                
                url = self.extract_url_from_element(element, url_selectors)
                if not url:
                    continue
                
                # Create article with validation
                article = self.create_article(title, perex, url)
                if article:
                    articles.append(article)
                    
            except Exception as e:
                self.logger.warning(f"Error parsing article element: {e}")
                continue
        
        return articles


# Factory function for backward compatibility
async def scrape_novinky() -> List[ArticleCreate]:
    """Factory function to maintain backward compatibility."""
    scraper = NovinkyScraper()
    return await scraper.scrape()
