from typing import List
from bs4 import BeautifulSoup
from .....core.models import ArticleCreate
from .....core.logging_handler import get_logger
from ..base import BaseScraper

logger = get_logger(__name__)


class SeznamZpravyScraper(BaseScraper):
    """Scraper for seznamzpravy.cz news website."""
    
    def __init__(self):
        super().__init__("seznamzpravy", "https://www.seznamzpravy.cz")
    
    async def extract_articles(self, soup: BeautifulSoup, page) -> List[ArticleCreate]:
        """Extract articles from seznamzpravy.cz with comprehensive selectors."""
        articles = []
        
        # Seznam has lots of dynamic content, scroll more
        await self.scroll_page(page, max_scrolls=5)
        
        # Get updated content after scrolling
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Seznam Zprávy specific selectors
        article_selectors = [
            # Primary containers
            'article',
            '.article',
            '.story',
            '.news-item',
            '.item',
            # Seznam specific classes
            '.feed-item',
            '.article-feed',
            '.story-feed',
            '.news-feed',
            '.content-item',
            '.article-preview',
            '.story-preview',
            '.listing-item',
            # Generic selectors
            '[class*="article"]',
            '[class*="story"]',
            '[class*="item"]',
            '[class*="feed"]',
            '.teaser',
            '.entry',
            '.post',
            # Data attributes
            '[data-article]',
            '[data-story]',
            '[data-feed-item]'
        ]
        
        elements = self.find_article_elements(soup, article_selectors)
        logger.info(f"Found {len(elements)} potential article elements on Seznam Zprávy")
        
        for element in elements[:80]:  # Process up to 80 articles
            try:
                # Enhanced title extraction for Seznam Zprávy
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
                    '.feed-title a', '.feed-title',
                    # Seznam specific URL patterns
                    'a[href*="/clanek/"]', 'a[href*="/zpravy/"]',
                    'a[href*="/sport/"]', 'a[href*="/ekonomika/"]',
                    'a[href*="/kultura/"]', 'a[href*="/zahranici/"]',
                    'a[href*="/domaci/"]', 'a[href*="/politika/"]',
                    # Class-based title selectors
                    'a.title', 'a.headline', 'a.article-link',
                    # Fallback selectors
                    'a[title]', '.link-title', '.news-title'
                ]
                
                title = self.extract_title_from_element(element, title_selectors)
                if not title:
                    continue
                
                # Extract perex/summary with Seznam-specific selectors
                perex_selectors = [
                    '.perex', '.summary', '.excerpt', '.abstract', '.description',
                    '.article-perex', '.story-perex', '.feed-perex',
                    '.article-summary', '.story-summary',
                    '.content-summary', '.article-description',
                    'p.perex', 'p.summary', 'p.excerpt',
                    'p', '.content p', '.lead', '.intro'
                ]
                
                perex = self.extract_perex_from_element(element, perex_selectors)
                
                # Extract URL with Seznam-specific selectors
                url_selectors = [
                    # Title links
                    'h1 a', 'h2 a', 'h3 a', 'h4 a', 'h5 a',
                    '.title a', '.headline a', '.article-title a',
                    '.story-title a', '.entry-title a', '.feed-title a',
                    # Seznam specific URL patterns
                    'a[href*="/clanek/"]', 'a[href*="/zpravy/"]',
                    'a[href*="/sport/"]', 'a[href*="/ekonomika/"]',
                    'a[href*="/kultura/"]', 'a[href*="/zahranici/"]',
                    'a[href*="/domaci/"]', 'a[href*="/politika/"]',
                    # Generic link selectors
                    'a.article-link', 'a.story-link', 'a.feed-link',
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
        
        logger.info(f"Successfully extracted {len(articles)} articles from Seznam Zprávy")
        return articles


# Factory function for backward compatibility
async def scrape_seznamzpravy() -> List[ArticleCreate]:
    """Factory function to maintain backward compatibility."""
    scraper = SeznamZpravyScraper()
    return await scraper.scrape()