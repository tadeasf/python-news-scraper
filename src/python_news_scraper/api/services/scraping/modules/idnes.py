from typing import List
from bs4 import BeautifulSoup
from .....core.models import ArticleCreate
from .....core.logging_handler import get_logger
from ..base import BaseScraper

logger = get_logger(__name__)


class IdnesScraper(BaseScraper):
    """Scraper for idnes.cz news website."""
    
    def __init__(self):
        super().__init__("idnes", "https://www.idnes.cz")
    
    async def extract_articles(self, soup: BeautifulSoup, page) -> List[ArticleCreate]:
        """Extract articles from idnes.cz with enhanced selectors."""
        articles = []
        
        # iDNES has lots of dynamic content, scroll more
        await self.scroll_page(page, max_scrolls=5)
        
        # Get updated content after scrolling
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Enhanced selectors based on iDNES.cz structure - modern Czech portal
        article_selectors = [
            # Primary containers
            'article',
            '.article',
            '.story',
            '.news-item',
            '.item',
            # iDNES specific classes
            '.art',
            '.c-article-item',
            '.art-item',
            '.story-item',
            '.zprava',
            '.clanek',
            '.content-item',
            '.listing-item',
            '.teaser',
            '.article-teaser',
            '.feed-item',
            # Modern iDNES selectors
            '.hp-article',
            '.hp-news',
            '.hp-story',
            '.homepage-article',
            '.homepage-news',
            # Generic attribute-based selectors
            '[class*="article"]',
            '[class*="story"]',
            '[class*="zprava"]',
            '[class*="clanek"]',
            '[class*="art"]',
            '[data-article]',
            '[data-story]',
            '.entry',
            '.post'
        ]
        
        elements = self.find_article_elements(soup, article_selectors)
        logger.info(f"Found {len(elements)} potential article elements on iDNES.cz")
        
        for element in elements[:80]:  # Process up to 80 articles
            try:
                # Enhanced title extraction for iDNES.cz
                title_selectors = [
                    # Headlines with links
                    'h1 a', 'h2 a', 'h3 a', 'h4 a', 'h5 a',
                    # Direct headlines
                    'h1', 'h2', 'h3', 'h4', 'h5',
                    # Common class-based selectors
                    '.title a', '.headline a', '.title', '.headline',
                    '.article-title a', '.article-title',
                    '.story-title a', '.story-title',
                    '.art-title a', '.art-title',
                    '.c-article-item__title a', '.c-article-item__title',
                    # iDNES specific URL patterns and links
                    'a[href*=".idnes.cz"]',
                    'a[href*="/zpravy/"]', 'a[href*="/clanek/"]',
                    'a[href*="/ekonomika/"]', 'a[href*="/sport/"]',
                    'a[href*="/kultura/"]', 'a[href*="/zahranici/"]',
                    'a[href*="/regiony/"]', 'a[href*="/auto/"]',
                    'a[href*="/tech/"]', 'a[href*="/bydleni/"]',
                    # Link classes
                    'a.art-link', 'a.c-article-item__link',
                    'a.article-link', 'a.story-link',
                    'a.teaser-link', 'a.item-link',
                    # Fallback selectors
                    'a[title]', '.link-title', '.news-title'
                ]
                
                title = self.extract_title_from_element(element, title_selectors)
                if not title:
                    continue
                
                # Enhanced perex/summary extraction for iDNES.cz
                perex_selectors = [
                    '.perex', '.summary', '.excerpt', '.abstract', '.description',
                    '.art-perex', '.article-perex', '.story-perex',
                    '.c-article-item__perex', '.c-article-item__summary',
                    '.teaser-perex', '.item-perex', '.content-perex',
                    'p.perex', 'p.summary', 'p.excerpt', 'p.description',
                    'p', '.content p', '.lead', '.intro', '.deck'
                ]
                
                perex = self.extract_perex_from_element(element, perex_selectors)
                
                # Enhanced URL extraction for iDNES.cz
                url_selectors = [
                    # Title links
                    'h1 a', 'h2 a', 'h3 a', 'h4 a', 'h5 a',
                    '.title a', '.headline a', '.article-title a',
                    '.story-title a', '.art-title a',
                    '.c-article-item__title a',
                    # iDNES specific URL patterns
                    'a[href*=".idnes.cz"]',
                    'a[href*="/zpravy/"]', 'a[href*="/clanek/"]',
                    'a[href*="/ekonomika/"]', 'a[href*="/sport/"]',
                    'a[href*="/kultura/"]', 'a[href*="/zahranici/"]',
                    'a[href*="/regiony/"]', 'a[href*="/auto/"]',
                    'a[href*="/tech/"]', 'a[href*="/bydleni/"]',
                    # Link classes
                    'a.art-link', 'a.c-article-item__link',
                    'a.article-link', 'a.story-link',
                    'a.teaser-link', 'a.item-link',
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
        
        logger.info(f"Successfully extracted {len(articles)} articles from iDNES.cz")
        return articles


# Factory function for backward compatibility
async def scrape_idnes() -> List[ArticleCreate]:
    """Factory function to maintain backward compatibility."""
    scraper = IdnesScraper()
    return await scraper.scrape()