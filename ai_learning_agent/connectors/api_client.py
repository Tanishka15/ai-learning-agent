"""
API Client Module

Provides standardized API integration for various external services
including Wikipedia, educational APIs, and other knowledge sources.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
import json
from dataclasses import dataclass

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


@dataclass
class APIResponse:
    """Represents a response from an API call."""
    success: bool
    data: Dict[str, Any]
    status_code: int
    error_message: Optional[str] = None
    source: str = ""


class APIClient:
    """
    Unified API client for accessing various external data sources.
    
    Supports:
    - Wikipedia API
    - Educational content APIs
    - Research paper APIs
    - General REST APIs
    """
    
    def __init__(self, config):
        """Initialize the API client."""
        self.config = config
        self.logger = logging.getLogger("api_client")
        
        # API endpoints
        self.endpoints = {
            'wikipedia': 'https://en.wikipedia.org/api/rest_v1',
            'wikidata': 'https://www.wikidata.org/w/api.php',
            'openlibrary': 'https://openlibrary.org/api',
            'arxiv': 'http://export.arxiv.org/api/query'
        }
        
        # Rate limiting
        self.rate_limits = {
            'wikipedia': 1.0,  # seconds between requests
            'default': 1.0
        }
        
        self.last_request_time = {}
        
        # HTTP client
        self.client = None
        
        self.logger.info("API client initialized")
    
    async def get_wikipedia_content(self, topic: str) -> Optional[Dict[str, Any]]:
        """
        Get content from Wikipedia for a given topic.
        
        Args:
            topic: The topic to search for
            
        Returns:
            Dictionary with Wikipedia content or None if not found
        """
        self.logger.info(f"Fetching Wikipedia content for: {topic}")
        
        try:
            # Search for the article first
            search_url = f"{self.endpoints['wikipedia']}/page/summary/{topic.replace(' ', '_')}"
            
            response = await self._make_request('GET', search_url, source='wikipedia')
            
            if response.success:
                return {
                    'source': 'wikipedia',
                    'title': response.data.get('title', topic),
                    'content': response.data.get('extract', ''),
                    'url': response.data.get('content_urls', {}).get('desktop', {}).get('page', ''),
                    'summary': response.data.get('extract', ''),
                    'metadata': {
                        'pageid': response.data.get('pageid'),
                        'lang': response.data.get('lang', 'en'),
                        'timestamp': response.data.get('timestamp')
                    }
                }
            else:
                self.logger.warning(f"Wikipedia content not found for: {topic}")
                return None
        
        except Exception as e:
            self.logger.error(f"Error fetching Wikipedia content: {e}")
            return None
    
    async def search_arxiv(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for academic papers on arXiv.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of paper information
        """
        self.logger.info(f"Searching arXiv for: {query}")
        
        try:
            params = {
                'search_query': f'all:{query}',
                'start': 0,
                'max_results': max_results,
                'sortBy': 'relevance',
                'sortOrder': 'descending'
            }
            
            url = f"{self.endpoints['arxiv']}"
            response = await self._make_request('GET', url, params=params, source='arxiv')
            
            if response.success:
                # Parse XML response (simplified)
                papers = self._parse_arxiv_response(response.data)
                return papers
            else:
                return []
        
        except Exception as e:
            self.logger.error(f"Error searching arXiv: {e}")
            return []
    
    async def get_educational_content(self, topic: str, source: str = 'khan_academy') -> Optional[Dict[str, Any]]:
        """
        Get educational content from various educational platforms.
        
        Args:
            topic: The topic to search for
            source: Educational source to query
            
        Returns:
            Educational content dictionary
        """
        self.logger.info(f"Fetching educational content for {topic} from {source}")
        
        # This is a placeholder implementation
        # In a real system, you'd integrate with actual educational APIs
        
        educational_content = {
            'source': source,
            'topic': topic,
            'content': f"Educational content about {topic} would be fetched from {source}",
            'difficulty_level': 'beginner',
            'estimated_time': 30,
            'concepts': [topic],
            'prerequisites': [],
            'related_topics': []
        }
        
        return educational_content
    
    async def search_open_library(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for books in Open Library.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of book information
        """
        self.logger.info(f"Searching Open Library for: {query}")
        
        try:
            url = f"{self.endpoints['openlibrary']}/books"
            params = {
                'q': query,
                'limit': limit,
                'format': 'json'
            }
            
            response = await self._make_request('GET', url, params=params, source='openlibrary')
            
            if response.success and 'docs' in response.data:
                books = []
                for doc in response.data['docs'][:limit]:
                    books.append({
                        'title': doc.get('title', ''),
                        'author': doc.get('author_name', []),
                        'publish_year': doc.get('first_publish_year'),
                        'subjects': doc.get('subject', []),
                        'isbn': doc.get('isbn', []),
                        'url': f"https://openlibrary.org{doc.get('key', '')}"
                    })
                return books
            else:
                return []
        
        except Exception as e:
            self.logger.error(f"Error searching Open Library: {e}")
            return []
    
    async def get_wikidata_info(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get structured data from Wikidata.
        
        Args:
            entity_id: Wikidata entity ID (e.g., Q42 for Douglas Adams)
            
        Returns:
            Structured entity data
        """
        self.logger.info(f"Fetching Wikidata info for entity: {entity_id}")
        
        try:
            params = {
                'action': 'wbgetentities',
                'ids': entity_id,
                'format': 'json',
                'languages': 'en'
            }
            
            response = await self._make_request('GET', self.endpoints['wikidata'], params=params, source='wikidata')
            
            if response.success and 'entities' in response.data:
                entity = response.data['entities'].get(entity_id, {})
                
                if entity:
                    return {
                        'id': entity_id,
                        'label': entity.get('labels', {}).get('en', {}).get('value', ''),
                        'description': entity.get('descriptions', {}).get('en', {}).get('value', ''),
                        'aliases': [alias.get('value', '') for alias in entity.get('aliases', {}).get('en', [])],
                        'claims': self._parse_wikidata_claims(entity.get('claims', {})),
                        'sitelinks': entity.get('sitelinks', {})
                    }
            
            return None
        
        except Exception as e:
            self.logger.error(f"Error fetching Wikidata info: {e}")
            return None
    
    async def _make_request(self, method: str, url: str, params: Optional[Dict] = None, 
                           data: Optional[Dict] = None, source: str = 'default') -> APIResponse:
        """
        Make an HTTP request with rate limiting and error handling.
        
        Args:
            method: HTTP method
            url: Request URL
            params: Query parameters
            data: Request body data
            source: API source for rate limiting
            
        Returns:
            APIResponse object
        """
        # Rate limiting
        await self._respect_rate_limit(source)
        
        try:
            if not self.client:
                if HAS_AIOHTTP:
                    self.client = aiohttp.ClientSession(
                        timeout=aiohttp.ClientTimeout(total=30)
                    )
                elif HAS_HTTPX:
                    self.client = httpx.AsyncClient(timeout=30.0)
                else:
                    # Fallback to basic implementation
                    return APIResponse(
                        success=False,
                        data={},
                        status_code=0,
                        error_message="No HTTP client available",
                        source=source
                    )
            
            # Make request based on available client
            if HAS_AIOHTTP and isinstance(self.client, aiohttp.ClientSession):
                async with self.client.request(method, url, params=params, json=data) as response:
                    status_code = response.status
                    
                    if response.content_type == 'application/json':
                        response_data = await response.json()
                    else:
                        response_data = {'text': await response.text()}
                    
                    return APIResponse(
                        success=200 <= status_code < 300,
                        data=response_data,
                        status_code=status_code,
                        source=source
                    )
            
            elif HAS_HTTPX and isinstance(self.client, httpx.AsyncClient):
                response = await self.client.request(method, url, params=params, json=data)
                
                try:
                    response_data = response.json()
                except:
                    response_data = {'text': response.text}
                
                return APIResponse(
                    success=200 <= response.status_code < 300,
                    data=response_data,
                    status_code=response.status_code,
                    source=source
                )
        
        except Exception as e:
            self.logger.error(f"Request error for {url}: {e}")
            return APIResponse(
                success=False,
                data={},
                status_code=0,
                error_message=str(e),
                source=source
            )
    
    async def _respect_rate_limit(self, source: str) -> None:
        """Ensure rate limiting for API requests."""
        delay = self.rate_limits.get(source, self.rate_limits['default'])
        
        if source in self.last_request_time:
            time_since_last = asyncio.get_event_loop().time() - self.last_request_time[source]
            if time_since_last < delay:
                await asyncio.sleep(delay - time_since_last)
        
        self.last_request_time[source] = asyncio.get_event_loop().time()
    
    def _parse_arxiv_response(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse arXiv API XML response (simplified)."""
        # This is a simplified parser - in reality, you'd parse XML properly
        papers = []
        
        # Placeholder implementation
        for i in range(3):  # Simulate some papers
            papers.append({
                'title': f"Sample Paper {i+1}",
                'authors': [f"Author {i+1}"],
                'abstract': f"Abstract for paper {i+1} about the queried topic",
                'url': f"https://arxiv.org/abs/sample{i+1}",
                'published': "2023-01-01",
                'categories': ["cs.AI"]
            })
        
        return papers
    
    def _parse_wikidata_claims(self, claims: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Wikidata claims into a more readable format."""
        parsed_claims = {}
        
        for property_id, claim_list in claims.items():
            parsed_values = []
            for claim in claim_list:
                if 'mainsnak' in claim and 'datavalue' in claim['mainsnak']:
                    value = claim['mainsnak']['datavalue'].get('value')
                    parsed_values.append(value)
            
            if parsed_values:
                parsed_claims[property_id] = parsed_values
        
        return parsed_claims
    
    async def close(self):
        """Clean up HTTP client resources."""
        if self.client:
            if hasattr(self.client, 'close'):
                await self.client.close()
        
        self.logger.info("API client resources cleaned up")