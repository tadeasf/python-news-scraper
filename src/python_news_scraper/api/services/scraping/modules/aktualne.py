from typing import List
from bs4 import BeautifulSoup
from .....core.models import ArticleCreate
from .....core.logging_handler import get_logger
from ..base import BaseScraper

logger = get_logger(__name__)


class AktualneScraper(BaseScraper):
    """Scraper for aktualne.cz news website."""
    
    def __init__(self):
        super().__init__("aktualne", "https://aktualne.cz")
    
    async def extract_articles(self, soup: BeautifulSoup, page) -> List[ArticleCreate]:
        """Extract articles from aktualne.cz with improved selectors."""
        articles = []
        
        # Scroll to load more content - aktualne.cz has lots of lazy loading
        await self.scroll_page(page, max_scrolls=5)
        
        # Get updated content after scrolling
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Enhanced selectors based on aktualne.cz structure
        article_selectors = [
            # Primary article containers
            'article',
            '.article',
            '.story',
            '.post',
            '.zprava',
            # Common aktualne.cz specific classes
            '.article-preview',
            '.article-item',
            '.content-article',
            '.news-story',
            '.listing-article',
            # Generic content selectors
            '[class*="article"]',
            '[class*="story"]',
            '[class*="zprava"]',
            '.content-item',
            '.news-item',
            '.listing-item',
            # Additional fallback selectors
            '.teaser',
            '.content-box',
            '[data-article]',
            '.entry'
        ]
        
        elements = self.find_article_elements(soup, article_selectors)
        
        logger.info(f"Found {len(elements)} potential article elements on aktualne.cz")
        
        for element in elements[:80]:  # Process up to 80 articles
            try:
                # Enhanced title extraction for aktualne.cz
                title_selectors = [
                    # Headlines with links
                    'h1 a', 'h2 a', 'h3 a', 'h4 a',
                    # Direct headlines
                    'h1', 'h2', 'h3', 'h4',
                    # Common class-based selectors
                    '.title a', '.headline a', '.title', '.headline',
                    '.article-title a', '.article-title',
                    '.story-title a', '.story-title',
                    '.entry-title a', '.entry-title',
                    # aktualne.cz specific URL patterns
                    'a[href*="/zpravy/"]', 'a[href*="/sport/"]', 
                    'a[href*="/magazin/"]', 'a[href*="/ekonomika/"]',
                    'a[href*="/kultura/"]', 'a[href*="/zahranici/"]',
                    # Fallback selectors
                    'a[title]', '.link-title'
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
                    'p',
                    '.content p'
                ]
                
                perex = self.extract_perex_from_element(element, perex_selectors)
                
                # Extract URL
                url_selectors = [
                    'h1 a',
                    'h2 a',
                    'h3 a',
                    '.title a',
                    '.headline a',
                    'a[href*="/zpravy/"]',
                    'a[href*="/sport/"]',
                    'a[href*="/magazin/"]',
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
async def scrape_aktualne() -> List[ArticleCreate]:
    """Factory function to maintain backward compatibility."""
    scraper = AktualneScraper()
    return await scraper.scrape()
