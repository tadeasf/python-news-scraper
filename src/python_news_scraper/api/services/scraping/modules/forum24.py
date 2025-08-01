from typing import List
from bs4 import BeautifulSoup
from .....core.models import ArticleCreate
from .....core.logging_handler import get_logger
from ..base import BaseScraper

logger = get_logger(__name__)


class Forum24Scraper(BaseScraper):
    """Scraper for forum24.cz news website (political commentary)."""
    
    def __init__(self):
        super().__init__("forum24", "https://www.forum24.cz")
    
    async def extract_articles(self, soup: BeautifulSoup, page) -> List[ArticleCreate]:
        """Extract articles from forum24.cz with political news specific selectors."""
        articles = []
        
        # Forum24 has political commentary with dynamic content
        await self.scroll_page(page, max_scrolls=4)
        
        # Get updated content after scrolling
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Forum24 specific selectors - political commentary structure
        article_selectors = [
            # Primary containers
            'article',
            '.article',
            '.story',
            '.news-item',
            '.item',
            # Forum24 specific classes
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
            # Political news specific
            '.political-article',
            '.commentary-article',
            '.opinion-article',
            '.editorial-article',
            # Generic selectors
            '[class*="article"]',
            '[class*="story"]',
            '[class*="item"]',
            '[class*="teaser"]',
            '[class*="card"]',
            '[class*="news"]',
            '[class*="commentary"]',
            '[class*="opinion"]',
            '.entry',
            '.post',
            # Data attributes
            '[data-article]',
            '[data-story]',
            '[data-item]'
        ]
        
        elements = self.find_article_elements(soup, article_selectors)
        logger.info(f"Found {len(elements)} potential article elements on Forum24.cz")
        
        for element in elements[:70]:  # Process up to 70 articles for Forum24
            try:
                # Enhanced title extraction for Forum24.cz
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
                    '.commentary-title a', '.commentary-title',
                    # Forum24 specific URL patterns
                    'a[href*="/clanek/"]', 'a[href*="/zpravy/"]',
                    'a[href*="/politika/"]', 'a[href*="/komentare/"]',
                    'a[href*="/nazory/"]', 'a[href*="/analyzy/"]',
                    'a[href*="/zahranici/"]', 'a[href*="/domaci/"]',
                    'a[href*="/ekonomika/"]', 'a[href*="/kultura/"]',
                    'a[href*="/editorial/"]', 'a[href*="/opinion/"]',
                    # Class-based title selectors
                    'a.title', 'a.headline', 'a.article-link',
                    'a.story-link', 'a.teaser-link', 'a.card-link',
                    # Fallback selectors
                    'a[title]', '.link-title'
                ]
                
                title = self.extract_title_from_element(element, title_selectors)
                if not title:
                    continue
                
                # Extract perex/summary with Forum24-specific selectors
                perex_selectors = [
                    '.perex', '.summary', '.excerpt', '.abstract', '.description',
                    '.article-perex', '.story-perex', '.teaser-perex',
                    '.article-summary', '.story-summary', '.teaser-summary',
                    '.content-summary', '.article-description',
                    '.teaser-description', '.item-description',
                    '.card-description', '.card-summary',
                    '.commentary-perex', '.commentary-summary',
                    '.opinion-perex', '.editorial-perex',
                    'p.perex', 'p.summary', 'p.excerpt', 'p.description',
                    'p', '.content p', '.lead', '.intro', '.deck'
                ]
                
                perex = self.extract_perex_from_element(element, perex_selectors)
                
                # Extract URL with Forum24-specific selectors
                url_selectors = [
                    # Title links
                    'h1 a', 'h2 a', 'h3 a', 'h4 a', 'h5 a',
                    '.title a', '.headline a', '.article-title a',
                    '.story-title a', '.entry-title a', '.teaser-title a',
                    '.card-title a', '.news-title a', '.commentary-title a',
                    # Forum24 specific URL patterns
                    'a[href*="/clanek/"]', 'a[href*="/zpravy/"]',
                    'a[href*="/politika/"]', 'a[href*="/komentare/"]',
                    'a[href*="/nazory/"]', 'a[href*="/analyzy/"]',
                    'a[href*="/zahranici/"]', 'a[href*="/domaci/"]',
                    'a[href*="/ekonomika/"]', 'a[href*="/kultura/"]',
                    'a[href*="/editorial/"]', 'a[href*="/opinion/"]',
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
        
        logger.info(f"Successfully extracted {len(articles)} articles from Forum24.cz")
        return articles


# Factory function for backward compatibility
async def scrape_forum24() -> List[ArticleCreate]:
    """Factory function to maintain backward compatibility."""
    scraper = Forum24Scraper()
    return await scraper.scrape()