from typing import List
from bs4 import BeautifulSoup
from .....core.models import ArticleCreate
from .....core.logging_handler import get_logger
from ..base import BaseScraper

logger = get_logger(__name__)


class E15Scraper(BaseScraper):
    """Scraper for e15.cz news website (business and economic news)."""
    
    def __init__(self):
        super().__init__("e15", "https://www.e15.cz")
    
    async def extract_articles(self, soup: BeautifulSoup, page) -> List[ArticleCreate]:
        """Extract articles from e15.cz with business news specific selectors."""
        articles = []
        
        # E15 has business content with modern layout
        await self.scroll_page(page, max_scrolls=4)
        
        # Get updated content after scrolling
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # E15 specific selectors - business news structure
        article_selectors = [
            # Primary containers
            'article',
            '.article',
            '.story',
            '.news-item',
            '.item',
            # E15 specific classes
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
            # Business news specific
            '.business-article',
            '.economic-article',
            '.finance-article',
            '.market-article',
            '.economic-news',
            '.business-news',
            # Generic selectors
            '[class*="article"]',
            '[class*="story"]',
            '[class*="item"]',
            '[class*="teaser"]',
            '[class*="card"]',
            '[class*="news"]',
            '[class*="business"]',
            '[class*="economic"]',
            '[class*="finance"]',
            '.entry',
            '.post',
            # Data attributes
            '[data-article]',
            '[data-story]',
            '[data-item]'
        ]
        
        elements = self.find_article_elements(soup, article_selectors)
        logger.info(f"Found {len(elements)} potential article elements on E15.cz")
        
        for element in elements[:70]:  # Process up to 70 articles for E15
            try:
                # Enhanced title extraction for E15.cz
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
                    # E15 specific URL patterns (business focus)
                    'a[href*="/clanek/"]', 'a[href*="/zpravy/"]',
                    'a[href*="/ekonomika/"]', 'a[href*="/finance/"]',
                    'a[href*="/business/"]', 'a[href*="/trhy/"]',
                    'a[href*="/firmy/"]', 'a[href*="/akcie/"]',
                    'a[href*="/burza/"]', 'a[href*="/investice/"]',
                    'a[href*="/banky/"]', 'a[href*="/pojistovny/"]',
                    'a[href*="/reality/"]', 'a[href*="/auto/"]',
                    'a[href*="/tech/"]', 'a[href*="/startup/"]',
                    # Class-based title selectors
                    'a.title', 'a.headline', 'a.article-link',
                    'a.story-link', 'a.teaser-link', 'a.card-link',
                    # Fallback selectors
                    'a[title]', '.link-title'
                ]
                
                title = self.extract_title_from_element(element, title_selectors)
                if not title:
                    continue
                
                # Extract perex/summary with E15-specific selectors
                perex_selectors = [
                    '.perex', '.summary', '.excerpt', '.abstract', '.description',
                    '.article-perex', '.story-perex', '.teaser-perex',
                    '.article-summary', '.story-summary', '.teaser-summary',
                    '.content-summary', '.article-description',
                    '.teaser-description', '.item-description',
                    '.card-description', '.card-summary',
                    '.business-perex', '.economic-perex',
                    '.finance-perex', '.market-perex',
                    'p.perex', 'p.summary', 'p.excerpt', 'p.description',
                    'p', '.content p', '.lead', '.intro', '.deck'
                ]
                
                perex = self.extract_perex_from_element(element, perex_selectors)
                
                # Extract URL with E15-specific selectors
                url_selectors = [
                    # Title links
                    'h1 a', 'h2 a', 'h3 a', 'h4 a', 'h5 a',
                    '.title a', '.headline a', '.article-title a',
                    '.story-title a', '.entry-title a', '.teaser-title a',
                    '.card-title a', '.news-title a',
                    # E15 specific URL patterns (business focus)
                    'a[href*="/clanek/"]', 'a[href*="/zpravy/"]',
                    'a[href*="/ekonomika/"]', 'a[href*="/finance/"]',
                    'a[href*="/business/"]', 'a[href*="/trhy/"]',
                    'a[href*="/firmy/"]', 'a[href*="/akcie/"]',
                    'a[href*="/burza/"]', 'a[href*="/investice/"]',
                    'a[href*="/banky/"]', 'a[href*="/pojistovny/"]',
                    'a[href*="/reality/"]', 'a[href*="/auto/"]',
                    'a[href*="/tech/"]', 'a[href*="/startup/"]',
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
        
        logger.info(f"Successfully extracted {len(articles)} articles from E15.cz")
        return articles


# Factory function for backward compatibility
async def scrape_e15() -> List[ArticleCreate]:
    """Factory function to maintain backward compatibility."""
    scraper = E15Scraper()
    return await scraper.scrape()