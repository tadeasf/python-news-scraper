from typing import List
from bs4 import BeautifulSoup
from .....core.models import ArticleCreate
from .....core.logging_handler import get_logger
from ..base import BaseScraper

logger = get_logger(__name__)


class LidovkyScraper(BaseScraper):
    """Scraper for lidovky.cz news website."""
    
    def __init__(self):
        super().__init__("lidovky", "https://www.lidovky.cz")
    
    async def extract_articles(self, soup: BeautifulSoup, page) -> List[ArticleCreate]:
        """Extract articles from lidovky.cz with Lidovky-specific selectors."""
        articles = []
        
        # Lidovky has dynamic content loading
        await self.scroll_page(page, max_scrolls=4)
        
        # Get updated content after scrolling
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Lidovky specific selectors
        article_selectors = [
            # Primary containers
            'article',
            '.article',
            '.story',
            '.news-item',
            '.item',
            # Lidovky specific classes
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
            '.story-card',
            '.news-card',
            # Generic selectors
            '[class*="article"]',
            '[class*="story"]',
            '[class*="item"]',
            '[class*="teaser"]',
            '[class*="card"]',
            '.entry',
            '.post',
            # Data attributes
            '[data-article]',
            '[data-story]',
            '[data-item]'
        ]
        
        elements = self.find_article_elements(soup, article_selectors)
        logger.info(f"Found {len(elements)} potential article elements on Lidovky")
        
        for element in elements[:70]:  # Process up to 70 articles for Lidovky
            try:
                # Enhanced title extraction for Lidovky
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
                    # Lidovky specific URL patterns
                    'a[href*="/clanek/"]', 'a[href*="/zpravy/"]',
                    'a[href*="/domaci/"]', 'a[href*="/zahranici/"]',
                    'a[href*="/ekonomika/"]', 'a[href*="/kultura/"]',
                    'a[href*="/sport/"]', 'a[href*="/regiony/"]',
                    'a[href*="/komentare/"]', 'a[href*="/tema/"]',
                    'a[href*="/lifestyle/"]', 'a[href*="/auto/"]',
                    # Class-based title selectors
                    'a.title', 'a.headline', 'a.article-link',
                    'a.story-link', 'a.teaser-link', 'a.card-link',
                    # Fallback selectors
                    'a[title]', '.link-title', '.news-title'
                ]
                
                title = self.extract_title_from_element(element, title_selectors)
                if not title:
                    continue
                
                # Extract perex/summary with Lidovky-specific selectors
                perex_selectors = [
                    '.perex', '.summary', '.excerpt', '.abstract', '.description',
                    '.article-perex', '.story-perex', '.teaser-perex',
                    '.article-summary', '.story-summary', '.teaser-summary',
                    '.content-summary', '.article-description',
                    '.teaser-description', '.item-description',
                    '.card-description', '.card-summary',
                    'p.perex', 'p.summary', 'p.excerpt', 'p.description',
                    'p', '.content p', '.lead', '.intro', '.deck'
                ]
                
                perex = self.extract_perex_from_element(element, perex_selectors)
                
                # Extract URL with Lidovky-specific selectors
                url_selectors = [
                    # Title links
                    'h1 a', 'h2 a', 'h3 a', 'h4 a', 'h5 a',
                    '.title a', '.headline a', '.article-title a',
                    '.story-title a', '.entry-title a', '.teaser-title a',
                    '.card-title a',
                    # Lidovky specific URL patterns
                    'a[href*="/clanek/"]', 'a[href*="/zpravy/"]',
                    'a[href*="/domaci/"]', 'a[href*="/zahranici/"]',
                    'a[href*="/ekonomika/"]', 'a[href*="/kultura/"]',
                    'a[href*="/sport/"]', 'a[href*="/regiony/"]',
                    'a[href*="/komentare/"]', 'a[href*="/tema/"]',
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
        
        logger.info(f"Successfully extracted {len(articles)} articles from Lidovky")
        return articles


# Factory function for backward compatibility
async def scrape_lidovky() -> List[ArticleCreate]:
    """Factory function to maintain backward compatibility."""
    scraper = LidovkyScraper()
    return await scraper.scrape()