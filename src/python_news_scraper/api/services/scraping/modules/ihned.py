from typing import List
from bs4 import BeautifulSoup
from .....core.models import ArticleCreate
from ..base import BaseScraper


class IhnedScraper(BaseScraper):
    """Scraper for ihned.cz news website."""
    
    def __init__(self):
        super().__init__("ihned", "https://ihned.cz")
    
    async def extract_articles(self, soup: BeautifulSoup, page) -> List[ArticleCreate]:
        """Extract articles from ihned.cz."""
        articles = []
        
        # Scroll to load more content
        await self.scroll_page(page, max_scrolls=2)
        
        # Get updated content after scrolling
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Multiple selectors to find article elements on ihned.cz
        article_selectors = [
            'article',
            '.article',
            '.story',
            '.news-item',
            '.item',
            '[class*="article"]',
            '[class*="story"]',
            '[class*="item"]',
            '.content-item',
            '.listing-item',
            '.c-article',
            '.c-article-item',
            '.art'
        ]
        
        elements = self.find_article_elements(soup, article_selectors)
        
        for element in elements[:50]:  # Process up to 50 articles
            try:
                # Extract title using multiple strategies
                title_selectors = [
                    'h1 a',
                    'h2 a',
                    'h3 a',
                    'h4 a',
                    'h1',
                    'h2',
                    'h3',
                    'h4',
                    '.title a',
                    '.headline a',
                    '.title',
                    '.headline',
                    'a[href*="/c1-"]',
                    'a[href*="ihned.cz"]',
                    'a.art-link',
                    'a.c-article__link'
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
                    '.art-perex',
                    '.c-article__perex',
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
                    'a[href*="/c1-"]',
                    'a[href*="ihned.cz"]',
                    'a.art-link',
                    'a.c-article__link',
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
async def scrape_ihned() -> List[ArticleCreate]:
    """Factory function to maintain backward compatibility."""
    scraper = IhnedScraper()
    return await scraper.scrape()