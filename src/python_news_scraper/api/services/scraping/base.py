import asyncio
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from camoufox import AsyncCamoufox
from bs4 import BeautifulSoup
from ....core.models import ArticleCreate
from ....core.logging_handler import get_logger, async_catch

logger = get_logger(__name__)


class BaseScraper(ABC):
    """Base scraper class for news websites."""
    
    def __init__(self, source_name: str, base_url: str):
        self.source_name = source_name
        self.base_url = base_url
        self.logger = get_logger(f"{__name__}.{source_name}")
    
    @async_catch(reraise=False)
    async def scrape(self) -> List[ArticleCreate]:
        """Main scraping method that orchestrates the scraping process."""
        articles = []
        
        try:
            async with AsyncCamoufox(
                geoip=False,  # Disable geoip to avoid potential network issues
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accessibility',
                    '--disable-accessibility-events',
                    '--disable-high-contrast'
                ]
            ) as browser:
                page = await browser.new_page()
                
                # Set realistic viewport size
                await page.set_viewport_size({"width": 1920, "height": 1080})
                
                # Set a realistic user agent
                await page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                })
                
                # Navigate to the website with increased timeout
                await page.goto(self.base_url, wait_until="load", timeout=60000)
                
                # Wait for content to load and dynamic elements
                await asyncio.sleep(5)
                
                # Try to accept cookies or dismiss modals that might be blocking content
                await self._dismiss_modals(page)
                
                # Get page content
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Extract articles using source-specific logic
                articles = await self.extract_articles(soup, page)
                
        except Exception as e:
            self.logger.error(f"Error scraping {self.source_name}: {e}")
            
            # Add specific handling for common network errors
            error_str = str(e).lower()
            if 'ns_error_unknown_host' in error_str:
                self.logger.error(f"DNS resolution failed for {self.base_url}. Check internet connectivity and DNS settings.")
            elif 'timeout' in error_str:
                self.logger.error(f"Timeout connecting to {self.base_url}. The site might be slow or unreachable.")
            elif 'connection' in error_str:
                self.logger.error(f"Connection failed to {self.base_url}. Check firewall and proxy settings.")
        
        self.logger.info(f"Scraped {len(articles)} articles from {self.source_name}")
        return articles
    
    @abstractmethod
    async def extract_articles(self, soup: BeautifulSoup, page) -> List[ArticleCreate]:
        """Extract articles from the parsed HTML. Must be implemented by child classes."""
        pass
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        return text.strip().replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    
    def normalize_url(self, url: str) -> str:
        """Normalize relative URLs to absolute URLs."""
        if not url:
            return ""
        
        if url.startswith('/'):
            return f"{self.base_url.rstrip('/')}{url}"
        elif not url.startswith('http'):
            return f"{self.base_url.rstrip('/')}/{url.lstrip('/')}"
        
        return url
    
    def create_article(self, title: str, perex: str, url: str) -> Optional[ArticleCreate]:
        """Create an ArticleCreate object with validation."""
        title = self.clean_text(title)
        perex = self.clean_text(perex)
        url = self.normalize_url(url)
        
        # Basic validation
        if not title or len(title) < 10:
            return None
        
        if not url or not url.startswith('http'):
            return None
        
        return ArticleCreate(
            title=title,
            perex=perex[:500],  # Limit perex length
            source=self.source_name,
            url=url
        )
    
    async def _dismiss_modals(self, page) -> None:
        """Try to dismiss cookie banners and modals that might block content."""
        try:
            # Common selectors for cookie acceptance and modal dismissal
            dismiss_selectors = [
                'button[contains(text(), "Přijmout")]',  # Czech "Accept"
                'button[contains(text(), "Accept")]',
                'button[contains(text(), "Souhlasím")]',  # Czech "I agree"
                'button[id*="cookie"]',
                'button[class*="cookie"]',
                'button[class*="accept"]',
                'button[class*="consent"]',
                '.modal-close',
                '.close-modal',
                '[data-dismiss="modal"]',
                '.gdpr-accept',
                '.cookie-accept',
                '[aria-label="Close"]',
                '[aria-label="Zavřít"]'  # Czech "Close"
            ]
            
            for selector in dismiss_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button:
                        await button.click()
                        await asyncio.sleep(1)
                        self.logger.debug(f"Dismissed modal with selector: {selector}")
                        break
                except Exception:
                    continue
                    
        except Exception as e:
            self.logger.debug(f"Could not dismiss modals: {e}")
    
    async def scroll_page(self, page, max_scrolls: int = 4) -> None:
        """Scroll the page to load more content dynamically."""
        try:
            for i in range(max_scrolls):
                # Get current height
                prev_height = await page.evaluate("document.body.scrollHeight")
                
                # Scroll down gradually to trigger lazy loading
                await page.evaluate(f"window.scrollTo(0, {prev_height})")
                await asyncio.sleep(3)
                
                # Check if new content was loaded
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height == prev_height:
                    # No new content loaded, try scrolling to bottom completely
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(2)
                    break
                    
        except Exception as e:
            self.logger.debug(f"Error during scrolling: {e}")
    
    def find_article_elements(self, soup: BeautifulSoup, selectors: List[str]) -> List:
        """Find article elements using multiple selectors."""
        elements = []
        for selector in selectors:
            found = soup.select(selector)
            elements.extend(found)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_elements = []
        for elem in elements:
            elem_id = id(elem)
            if elem_id not in seen:
                seen.add(elem_id)
                unique_elements.append(elem)
        
        return unique_elements
    
    def extract_title_from_element(self, element, selectors: List[str]) -> str:
        """Extract title from element using multiple selectors."""
        for selector in selectors:
            title_elem = element.select_one(selector)
            if title_elem:
                title = self.clean_text(title_elem.get_text())
                if title and len(title) >= 10:
                    return title
        return ""
    
    def extract_perex_from_element(self, element, selectors: List[str]) -> str:
        """Extract perex/summary from element using multiple selectors."""
        for selector in selectors:
            perex_elem = element.select_one(selector)
            if perex_elem:
                perex = self.clean_text(perex_elem.get_text())
                if perex and len(perex) >= 20:
                    return perex
        return ""
    
    def extract_url_from_element(self, element, selectors: List[str]) -> str:
        """Extract URL from element using multiple selectors."""
        for selector in selectors:
            link_elem = element.select_one(selector)
            if link_elem and link_elem.get('href'):
                return link_elem['href']
        return ""
