"""
Web Scraper Module

Provides intelligent web scraping capabilities for gathering information
from various online sources while respecting robots.txt and rate limits.
"""

import asyncio
import aiohttp
import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
import time
import random

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False


@dataclass
class ScrapedContent:
    """Represents scraped content from a web page."""
    url: str
    title: str
    text: str
    metadata: Dict[str, Any]
    timestamp: float
    success: bool
    error_message: Optional[str] = None


@dataclass
class ScrapingTask:
    """Represents a web scraping task."""
    query: str
    max_pages: int
    target_domains: List[str]
    content_filters: List[str]
    priority: int = 1


class WebScraper:
    """
    Intelligent web scraper that can search and extract content from web pages.
    
    Features:
    - Respects robots.txt
    - Rate limiting
    - Multiple extraction methods (requests + BeautifulSoup, Selenium)
    - Content filtering and cleaning
    - Async operation for performance
    """
    
    def __init__(self, config):
        """Initialize the web scraper."""
        self.config = config
        self.logger = logging.getLogger("web_scraper")

        # Configuration
        ws_cfg = config.data_sources.web_scraping
        self.max_pages = getattr(ws_cfg, 'max_pages_per_search', 10)
        self.timeout = getattr(ws_cfg, 'timeout_seconds', 30)
        self.user_agent = getattr(ws_cfg, 'user_agent', 'AI-Learning-Agent/1.0')
        self.respect_robots = getattr(ws_cfg, 'respect_robots_txt', True)

        # Rate limiting
        self.last_request_time = {}
        self.min_delay = 1.0  # Minimum delay between requests to same domain

        # Session for connection pooling
        self.session = None

        # Selenium driver (initialized on demand)
        self.driver = None

        # Cache for robots.txt
        self.robots_cache = {}

        self.logger.info("Web scraper initialized")
    
    async def search_and_scrape(self, query: str, max_pages: Optional[int] = None) -> List[ScrapedContent]:
        """
        Search for content related to query and scrape the results.
        
        Args:
            query: Search query
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of scraped content
        """
        self.logger.info(f"Starting search and scrape for: {query}")
        
        max_pages = max_pages or self.max_pages
        
        # Get search URLs
        search_urls = await self._get_search_urls(query)
        
        # Limit to max_pages
        search_urls = search_urls[:max_pages]
        
        # Scrape pages concurrently
        scraped_content = await self._scrape_pages_concurrent(search_urls)
        
        # Filter and clean content
        filtered_content = self._filter_content(scraped_content, query)
        
        self.logger.info(f"Successfully scraped {len(filtered_content)} pages for query: {query}")
        return filtered_content
    
    async def scrape_url(self, url: str) -> ScrapedContent:
        """
        Scrape content from a specific URL.
        
        Args:
            url: URL to scrape
            
        Returns:
            ScrapedContent object
        """
        self.logger.info(f"Scraping URL: {url}")
        
        # Check robots.txt if enabled
        if self.respect_robots and not await self._check_robots_allowed(url):
            return ScrapedContent(
                url=url,
                title="",
                text="",
                metadata={},
                timestamp=time.time(),
                success=False,
                error_message="Blocked by robots.txt"
            )
        
        # Rate limiting
        await self._respect_rate_limit(url)
        
        # Try different scraping methods
        content = await self._scrape_with_requests(url)
        
        if not content.success and HAS_SELENIUM:
            content = await self._scrape_with_selenium(url)
        
        return content
    
    async def _get_search_urls(self, query: str) -> List[str]:
        """Get URLs from search engines for the given query."""
        search_urls = []
        
        # Build search URLs for different sources
        search_engines = [
            f"https://www.google.com/search?q={query.replace(' ', '+')}",
            f"https://duckduckgo.com/?q={query.replace(' ', '+')}",
            f"https://en.wikipedia.org/wiki/Special:Search?search={query.replace(' ', '+')}"
        ]
        
        # For demonstration, we'll use some educational domains
        # In a real implementation, you'd parse search engine results
        educational_domains = [
            f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}",
            f"https://www.khanacademy.org/search?page_search_query={query.replace(' ', '+')}",
            f"https://www.coursera.org/search?query={query.replace(' ', '+')}",
            f"https://www.edx.org/search?q={query.replace(' ', '+')}"
        ]
        
        search_urls.extend(educational_domains)
        
        # Add some general educational sites
        if "programming" in query.lower():
            search_urls.extend([
                f"https://stackoverflow.com/search?q={query.replace(' ', '+')}",
                f"https://developer.mozilla.org/en-US/search?q={query.replace(' ', '+')}"
            ])
        
        return search_urls[:self.max_pages]
    
    async def _scrape_pages_concurrent(self, urls: List[str]) -> List[ScrapedContent]:
        """Scrape multiple pages concurrently."""
        semaphore = asyncio.Semaphore(5)  # Limit concurrent requests
        
        async def scrape_with_semaphore(url):
            async with semaphore:
                return await self.scrape_url(url)
        
        tasks = [scrape_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_results = []
        for result in results:
            if isinstance(result, ScrapedContent):
                valid_results.append(result)
            else:
                self.logger.warning(f"Scraping error: {result}")
        
        return valid_results
    
    async def _scrape_with_requests(self, url: str) -> ScrapedContent:
        """Scrape content using aiohttp and BeautifulSoup."""
        if not HAS_BS4:
            return ScrapedContent(
                url=url,
                title="",
                text="",
                metadata={},
                timestamp=time.time(),
                success=False,
                error_message="BeautifulSoup not available"
            )
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    headers={'User-Agent': self.user_agent}
                )
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extract title
                    title_tag = soup.find('title')
                    title = title_tag.get_text().strip() if title_tag else ""
                    
                    # Remove script and style elements
                    for script in soup(["script", "style", "nav", "footer", "header"]):
                        script.decompose()
                    
                    # Extract text content
                    text = soup.get_text()
                    
                    # Clean up text
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    text = ' '.join(chunk for chunk in chunks if chunk)
                    
                    # Extract metadata
                    metadata = {
                        'url': url,
                        'status_code': response.status,
                        'content_type': response.headers.get('content-type', ''),
                        'content_length': len(text)
                    }
                    
                    return ScrapedContent(
                        url=url,
                        title=title,
                        text=text,
                        metadata=metadata,
                        timestamp=time.time(),
                        success=True
                    )
                else:
                    return ScrapedContent(
                        url=url,
                        title="",
                        text="",
                        metadata={'status_code': response.status},
                        timestamp=time.time(),
                        success=False,
                        error_message=f"HTTP {response.status}"
                    )
        
        except Exception as e:
            self.logger.error(f"Error scraping {url}: {e}")
            return ScrapedContent(
                url=url,
                title="",
                text="",
                metadata={},
                timestamp=time.time(),
                success=False,
                error_message=str(e)
            )
    
    async def _scrape_with_selenium(self, url: str) -> ScrapedContent:
        """Scrape content using Selenium for JavaScript-heavy sites."""
        if not HAS_SELENIUM:
            return ScrapedContent(
                url=url,
                title="",
                text="",
                metadata={},
                timestamp=time.time(),
                success=False,
                error_message="Selenium not available"
            )
        
        try:
            if not self.driver:
                options = Options()
                options.add_argument('--headless')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument(f'--user-agent={self.user_agent}')
                
                self.driver = webdriver.Chrome(options=options)
                self.driver.set_page_load_timeout(self.timeout)
            
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Extract content
            title = self.driver.title
            text = self.driver.find_element(By.TAG_NAME, "body").text
            
            metadata = {
                'url': url,
                'method': 'selenium',
                'content_length': len(text)
            }
            
            return ScrapedContent(
                url=url,
                title=title,
                text=text,
                metadata=metadata,
                timestamp=time.time(),
                success=True
            )
        
        except Exception as e:
            self.logger.error(f"Selenium scraping error for {url}: {e}")
            return ScrapedContent(
                url=url,
                title="",
                text="",
                metadata={},
                timestamp=time.time(),
                success=False,
                error_message=str(e)
            )
    
    def _filter_content(self, content_list: List[ScrapedContent], query: str) -> List[ScrapedContent]:
        """Filter and rank scraped content based on relevance."""
        filtered = []
        query_terms = query.lower().split()
        
        for content in content_list:
            if not content.success or len(content.text) < 100:
                continue
            
            # Calculate relevance score
            text_lower = content.text.lower()
            title_lower = content.title.lower()
            
            score = 0
            for term in query_terms:
                score += text_lower.count(term) * 1
                score += title_lower.count(term) * 3  # Title matches are more important
            
            # Minimum relevance threshold
            if score > 0:
                content.metadata['relevance_score'] = score
                filtered.append(content)
        
        # Sort by relevance
        filtered.sort(key=lambda x: x.metadata.get('relevance_score', 0), reverse=True)
        
        return filtered
    
    async def _check_robots_allowed(self, url: str) -> bool:
        """Check if scraping is allowed by robots.txt."""
        try:
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            if base_url in self.robots_cache:
                return self.robots_cache[base_url]
            
            robots_url = urljoin(base_url, '/robots.txt')
            
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=10),
                    headers={'User-Agent': self.user_agent}
                )
            
            async with self.session.get(robots_url) as response:
                if response.status == 200:
                    robots_content = await response.text()
                    # Simple robots.txt parsing (could be enhanced)
                    allowed = 'Disallow: /' not in robots_content
                else:
                    allowed = True  # If no robots.txt, assume allowed
            
            self.robots_cache[base_url] = allowed
            return allowed
        
        except Exception:
            # If we can't check robots.txt, assume allowed
            return True
    
    async def _respect_rate_limit(self, url: str) -> None:
        """Ensure rate limiting between requests to the same domain."""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        current_time = time.time()
        
        if domain in self.last_request_time:
            time_since_last = current_time - self.last_request_time[domain]
            if time_since_last < self.min_delay:
                sleep_time = self.min_delay - time_since_last
                await asyncio.sleep(sleep_time)
        
        self.last_request_time[domain] = time.time()
    
    async def close(self):
        """Clean up resources."""
        if self.session:
            await self.session.close()
        
        if self.driver:
            self.driver.quit()
        
        self.logger.info("Web scraper resources cleaned up")
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass