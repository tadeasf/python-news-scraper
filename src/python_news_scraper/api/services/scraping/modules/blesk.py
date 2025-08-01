from typing import List
from bs4 import BeautifulSoup
from .....core.models import ArticleCreate
from .....core.logging_handler import get_logger
from ..base import BaseScraper

logger = get_logger(__name__)


class BleskScraper(BaseScraper):
    """Scraper for blesk.cz news website."""
    
    def __init__(self):
        super().__init__("blesk", "https://www.blesk.cz")
    
    async def extract_articles(self, soup: BeautifulSoup, page) -> List[ArticleCreate]:
        """Extract articles from blesk.cz with tabloid-specific selectors."""
        articles = []
        
        # Scroll to load more content (tabloids often have more dynamic content)
        # Blesk has dynamic content loading, scroll more
        await self.scroll_page(page, max_scrolls=5)
        
        # Get updated content after scrolling
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Blesk.cz specific selectors (tabloid layout)
        article_selectors = [
            # Primary containers
            'article',
            '.article',
            '.story',
            '.news-item',
            '.item',
            '.clanek',
            # Blesk specific classes
            '.article-box',
            '.story-box',
            '.news-box',
            '.content-box',
            '.article-card',
            '.story-card',
            '.teaser-box',
            '.feed-item',
            '.listing-article',
            '.homepage-article',
            # Generic selectors
            '[class*="article"]',
            '[class*="story"]',
            '[class*="item"]',
            '[class*="box"]',
            '[class*="card"]',
            '.teaser',
            '.entry',
            '.post',
            # Data attributes
            '[data-article]',
            '[data-story]',
            '[data-id]'
        ]
        
        elements = self.find_article_elements(soup, article_selectors)
        logger.info(f"Found {len(elements)} potential article elements on Blesk.cz")
        
        for element in elements[:80]:  # Process more articles for tabloid content
            try:
                # Enhanced title extraction for Blesk.cz
                title_selectors = [
                    # Headlines with links
                    'h1 a', 'h2 a', 'h3 a', 'h4 a', 'h5 a', 'h6 a',
                    # Direct headlines
                    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                    # Common class-based selectors
                    '.title a', '.headline a', '.title', '.headline',
                    '.article-title a', '.article-title',
                    '.story-title a', '.story-title',
                    '.entry-title a', '.entry-title',
                    '.box-title a', '.box-title',
                    '.card-title a', '.card-title',
                    # Blesk specific URL patterns
                    'a[href*="/clanek/"]', 'a[href*="/zpravy/"]',
                    'a[href*="/sport/"]', 'a[href*="/celebrity/"]',
                    'a[href*="/krimi/"]', 'a[href*="/lifestyle/"]',
                    'a[href*="/zdravi/"]', 'a[href*="/reality/"]',
                    'a[href*="/auto/"]', 'a[href*="/bydleni/"]',
                    # Class-based title selectors
                    'a.title', 'a.headline', 'a.article-link',
                    'a.story-link', 'a.box-link',
                    # Strong/bold titles (common in tabloids)
                    'strong a', 'b a', '.bold a',
                    # Fallback selectors
                    'a[title]', '.link-title', '.news-title'
                ]
                
                title = self.extract_title_from_element(element, title_selectors)
                if not title:
                    continue
                
                # Extract perex/summary with Blesk-specific selectors
                perex_selectors = [
                    '.perex', '.summary', '.excerpt', '.abstract', '.description',
                    '.article-perex', '.story-perex', '.box-perex',
                    '.article-summary', '.story-summary', '.box-summary',
                    '.content-summary', '.article-description',
                    '.card-description', '.teaser-description',
                    'p.perex', 'p.summary', 'p.excerpt', 'p.description',
                    'p', '.content p', '.lead', '.intro', '.deck'
                ]
                
                perex = self.extract_perex_from_element(element, perex_selectors)
                
                # Extract URL with Blesk-specific selectors
                url_selectors = [
                    # Title links
                    'h1 a', 'h2 a', 'h3 a', 'h4 a', 'h5 a', 'h6 a',
                    '.title a', '.headline a', '.article-title a',
                    '.story-title a', '.entry-title a', '.box-title a',
                    '.card-title a',
                    # Blesk specific URL patterns
                    'a[href*="/clanek/"]', 'a[href*="/zpravy/"]',
                    'a[href*="/sport/"]', 'a[href*="/celebrity/"]',
                    'a[href*="/krimi/"]', 'a[href*="/lifestyle/"]',
                    'a[href*="/zdravi/"]', 'a[href*="/reality/"]',
                    'a[href*="/auto/"]', 'a[href*="/bydleni/"]',
                    # Generic link selectors
                    'a.article-link', 'a.story-link', 'a.box-link',
                    'a.card-link', 'a.teaser-link',
                    # Strong/bold links
                    'strong a', 'b a', '.bold a',
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
        
        logger.info(f"Successfully extracted {len(articles)} articles from Blesk.cz")
        return articles


# Factory function for backward compatibility
async def scrape_blesk() -> List[ArticleCreate]:
    """Factory function to maintain backward compatibility."""
    scraper = BleskScraper()
    return await scraper.scrape()