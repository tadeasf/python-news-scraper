from typing import List
from bs4 import BeautifulSoup
from .....core.models import ArticleCreate
from .....core.logging_handler import get_logger
from ..base import BaseScraper

logger = get_logger(__name__)


class CT24Scraper(BaseScraper):
    """Scraper for ct24.ceskatelevize.cz news website."""
    
    def __init__(self):
        super().__init__("ct24", "https://ct24.ceskatelevize.cz")
    
    async def extract_articles(self, soup: BeautifulSoup, page) -> List[ArticleCreate]:
        """Extract articles from ct24.ceskatelevize.cz with CT-specific selectors."""
        articles = []
        
        # CT24 has dynamic content, scroll to load more
        await self.scroll_page(page, max_scrolls=4)
        
        # Get updated content after scrolling
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # CT24 specific selectors - Czech Television structure
        article_selectors = [
            # Primary containers
            'article',
            '.article',
            '.story',
            '.news-item',
            '.item',
            # CT24 specific classes
            '.article-item',
            '.story-item',
            '.news-story',
            '.content-item',
            '.feed-item',
            '.listing-item',
            '.teaser',
            '.article-teaser',
            '.story-teaser',
            # Generic selectors
            '[class*="article"]',
            '[class*="story"]',
            '[class*="item"]',
            '[class*="teaser"]',
            '.entry',
            '.post',
            # Data attributes for CT
            '[data-article]',
            '[data-story]',
            '[data-item]'
        ]
        
        elements = self.find_article_elements(soup, article_selectors)
        logger.info(f"Found {len(elements)} potential article elements on CT24")
        
        for element in elements[:70]:  # Process up to 70 articles for CT24
            try:
                # Enhanced title extraction for CT24
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
                    # CT24 specific URL patterns (Czech TV structure)
                    'a[href*="/zpravy/"]', 'a[href*="/clanek/"]',
                    'a[href*="/domaci/"]', 'a[href*="/zahranici/"]',
                    'a[href*="/ekonomika/"]', 'a[href*="/kultura/"]',
                    'a[href*="/sport/"]', 'a[href*="/regiony/"]',
                    'a[href*="/koronavirus/"]', 'a[href*="/tema/"]',
                    # Class-based title selectors
                    'a.title', 'a.headline', 'a.article-link',
                    'a.story-link', 'a.teaser-link',
                    # Fallback selectors
                    'a[title]', '.link-title', '.news-title'
                ]
                
                title = self.extract_title_from_element(element, title_selectors)
                if not title:
                    continue
                
                # Extract perex/summary with CT24-specific selectors
                perex_selectors = [
                    '.perex', '.summary', '.excerpt', '.abstract', '.description',
                    '.article-perex', '.story-perex', '.teaser-perex',
                    '.article-summary', '.story-summary', '.teaser-summary',
                    '.content-summary', '.article-description',
                    '.teaser-description', '.item-description',
                    'p.perex', 'p.summary', 'p.excerpt', 'p.description',
                    'p', '.content p', '.lead', '.intro', '.deck'
                ]
                
                perex = self.extract_perex_from_element(element, perex_selectors)
                
                # Extract URL with CT24-specific selectors
                url_selectors = [
                    # Title links
                    'h1 a', 'h2 a', 'h3 a', 'h4 a', 'h5 a',
                    '.title a', '.headline a', '.article-title a',
                    '.story-title a', '.entry-title a', '.teaser-title a',
                    # CT24 specific URL patterns
                    'a[href*="/zpravy/"]', 'a[href*="/clanek/"]',
                    'a[href*="/domaci/"]', 'a[href*="/zahranici/"]',
                    'a[href*="/ekonomika/"]', 'a[href*="/kultura/"]',
                    'a[href*="/sport/"]', 'a[href*="/regiony/"]',
                    'a[href*="/koronavirus/"]', 'a[href*="/tema/"]',
                    # Generic link selectors
                    'a.article-link', 'a.story-link', 'a.teaser-link',
                    'a.item-link', 'a.content-link',
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
        
        logger.info(f"Successfully extracted {len(articles)} articles from CT24")
        return articles


# Factory function for backward compatibility
async def scrape_ct24() -> List[ArticleCreate]:
    """Factory function to maintain backward compatibility."""
    scraper = CT24Scraper()
    return await scraper.scrape()