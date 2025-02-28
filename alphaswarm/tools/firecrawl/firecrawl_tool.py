"""Firecrawl tools for AlphaSwarm."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from firecrawl import FirecrawlApp
from pydantic import BaseModel, Field

from alphaswarm.config import Config
from alphaswarm.tools.core.base_tool import BaseTool


class FirecrawlScrapeInput(BaseModel):
    """Input for FirecrawlScrape tool."""

    url: str = Field(..., description="URL to scrape")
    formats: List[str] = Field(
        default=["markdown"],
        description="Output formats to return (markdown, html, json, screenshot)",
    )
    extract_prompt: Optional[str] = Field(
        default=None,
        description="Optional prompt for LLM extraction (e.g., 'Extract all mentions of cryptocurrency names')",
    )


class FirecrawlCrawlInput(BaseModel):
    """Input for FirecrawlCrawl tool."""

    url: str = Field(..., description="URL to crawl")
    limit: int = Field(
        default=50,
        description="Maximum number of pages to crawl",
    )
    formats: List[str] = Field(
        default=["markdown"],
        description="Output formats to return (markdown, html, json, screenshot)",
    )
    extract_prompt: Optional[str] = Field(
        default=None,
        description="Optional prompt for LLM extraction (e.g., 'Extract all mentions of cryptocurrency names')",
    )


class FirecrawlSearchInput(BaseModel):
    """Input for FirecrawlSearch tool."""

    query: str = Field(..., description="Search query")
    platforms: List[str] = Field(
        default=["x.com", "reddit.com", "coingecko.com", "medium.com"],
        description="Platforms to search on",
    )
    limit: int = Field(
        default=50,
        description="Maximum number of results to return per platform",
    )
    extract_prompt: Optional[str] = Field(
        default=None,
        description="Optional prompt for LLM extraction (e.g., 'Extract all mentions of cryptocurrency names')",
    )


@dataclass
class FirecrawlResult:
    """Result from Firecrawl API."""

    content: Dict[str, Any]
    metadata: Dict[str, Any]


class FirecrawlScrape(BaseTool):
    """Tool to scrape a URL using Firecrawl."""

    name = "firecrawl_scrape"
    description = "Scrapes a URL and returns its content in various formats using Firecrawl."
    input_schema = FirecrawlScrapeInput

    def __init__(self, config: Optional[Config] = None):
        """Initialize the FirecrawlScrape tool.
        
        Args:
            config: AlphaSwarm config
        """
        super().__init__(config)
        self.api_key = self._get_api_key()
        self.firecrawl = FirecrawlApp(api_key=self.api_key)
        self.logger = logging.getLogger(__name__)

    def _get_api_key(self) -> str:
        """Get Firecrawl API key from config or environment."""
        if self.config and hasattr(self.config, "firecrawl_api_key"):
            return self.config.firecrawl_api_key
        
        import os
        api_key = os.environ.get("FIRECRAWL_API_KEY")
        if not api_key:
            raise ValueError("Firecrawl API key not found in config or environment")
        return api_key

    def _forward(self, url: str, formats: List[str], extract_prompt: Optional[str] = None) -> FirecrawlResult:
        """Forward the request to Firecrawl API."""
        params = {"formats": formats}
        
        if extract_prompt:
            params["jsonOptions"] = {
                "prompt": extract_prompt
            }
            
            # Make sure json format is included if we have an extraction prompt
            if "json" not in formats:
                params["formats"] = formats + ["json"]
        
        try:
            self.logger.info(f"Scraping URL: {url}")
            result = self.firecrawl.scrape_url(url, params=params)
            
            return FirecrawlResult(
                content=result,
                metadata=result.get("metadata", {})
            )
        except Exception as e:
            self.logger.error(f"Error scraping URL {url}: {str(e)}")
            raise

    def forward(self, url: str, formats: List[str] = None, extract_prompt: Optional[str] = None) -> FirecrawlResult:
        """Scrape a URL using Firecrawl.
        
        Args:
            url: URL to scrape
            formats: Output formats to return (markdown, html, json, screenshot)
            extract_prompt: Optional prompt for LLM extraction
            
        Returns:
            FirecrawlResult: Result from Firecrawl API
        """
        if formats is None:
            formats = ["markdown"]
            
        return self._forward(url, formats, extract_prompt)


class FirecrawlCrawl(BaseTool):
    """Tool to crawl a website using Firecrawl."""

    name = "firecrawl_crawl"
    description = "Crawls a website and returns content from all pages in various formats using Firecrawl."
    input_schema = FirecrawlCrawlInput

    def __init__(self, config: Optional[Config] = None):
        """Initialize the FirecrawlCrawl tool.
        
        Args:
            config: AlphaSwarm config
        """
        super().__init__(config)
        self.api_key = self._get_api_key()
        self.firecrawl = FirecrawlApp(api_key=self.api_key)
        self.logger = logging.getLogger(__name__)

    def _get_api_key(self) -> str:
        """Get Firecrawl API key from config or environment."""
        if self.config and hasattr(self.config, "firecrawl_api_key"):
            return self.config.firecrawl_api_key
        
        import os
        api_key = os.environ.get("FIRECRAWL_API_KEY")
        if not api_key:
            raise ValueError("Firecrawl API key not found in config or environment")
        return api_key

    def forward(self, url: str, limit: int = 50, formats: List[str] = None, extract_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Crawl a website using Firecrawl.
        
        Args:
            url: URL to crawl
            limit: Maximum number of pages to crawl
            formats: Output formats to return (markdown, html, json, screenshot)
            extract_prompt: Optional prompt for LLM extraction
            
        Returns:
            Dict[str, Any]: Result from Firecrawl API
        """
        if formats is None:
            formats = ["markdown"]
            
        params = {
            "limit": limit,
            "scrapeOptions": {"formats": formats}
        }
        
        if extract_prompt:
            params["scrapeOptions"]["jsonOptions"] = {
                "prompt": extract_prompt
            }
            
            # Make sure json format is included if we have an extraction prompt
            if "json" not in formats:
                params["scrapeOptions"]["formats"] = formats + ["json"]
        
        try:
            self.logger.info(f"Crawling URL: {url} with limit: {limit}")
            crawl_status = self.firecrawl.crawl_url(url, params=params, poll_interval=30)
            return crawl_status
        except Exception as e:
            self.logger.error(f"Error crawling URL {url}: {str(e)}")
            raise


class FirecrawlSearch(BaseTool):
    """Tool to search for content across multiple platforms using Firecrawl."""

    name = "firecrawl_search"
    description = "Searches for content across multiple platforms and returns results using Firecrawl."
    input_schema = FirecrawlSearchInput

    def __init__(self, config: Optional[Config] = None):
        """Initialize the FirecrawlSearch tool.
        
        Args:
            config: AlphaSwarm config
        """
        super().__init__(config)
        self.api_key = self._get_api_key()
        self.firecrawl = FirecrawlApp(api_key=self.api_key)
        self.scrape_tool = FirecrawlScrape(config)
        self.logger = logging.getLogger(__name__)

    def _get_api_key(self) -> str:
        """Get Firecrawl API key from config or environment."""
        if self.config and hasattr(self.config, "firecrawl_api_key"):
            return self.config.firecrawl_api_key
        
        import os
        api_key = os.environ.get("FIRECRAWL_API_KEY")
        if not api_key:
            raise ValueError("Firecrawl API key not found in config or environment")
        return api_key

    def forward(
        self, 
        query: str, 
        platforms: List[str] = None, 
        limit: int = 50, 
        extract_prompt: Optional[str] = None
    ) -> Dict[str, List[FirecrawlResult]]:
        """Search for content across multiple platforms using Firecrawl.
        
        Args:
            query: Search query
            platforms: Platforms to search on
            limit: Maximum number of results to return per platform
            extract_prompt: Optional prompt for LLM extraction
            
        Returns:
            Dict[str, List[FirecrawlResult]]: Results from Firecrawl API grouped by platform
        """
        if platforms is None:
            platforms = ["x.com", "reddit.com", "coingecko.com", "medium.com"]
            
        results = {}
        
        for platform in platforms:
            try:
                search_url = f"https://www.google.com/search?q=site:{platform}+{query}&num={limit}"
                self.logger.info(f"Searching on {platform} with query: {query}")
                
                # Use the scrape tool to get the search results
                search_results = self.scrape_tool.forward(
                    url=search_url,
                    formats=["markdown", "html"],
                    extract_prompt=f"Extract all search result URLs that point to {platform} and contain information about {query}"
                )
                
                # Process the search results to extract URLs
                if "json" in search_results.content and search_results.content["json"]:
                    # If we have structured data from the extraction
                    urls = self._extract_urls_from_json(search_results.content["json"], platform)
                else:
                    # Fall back to regex extraction from markdown
                    urls = self._extract_urls_from_markdown(search_results.content["markdown"], platform)
                
                # Limit the number of URLs to process
                urls = urls[:min(limit, len(urls))]
                
                # Scrape each URL
                platform_results = []
                for url in urls:
                    try:
                        result = self.scrape_tool.forward(
                            url=url,
                            formats=["markdown"],
                            extract_prompt=extract_prompt
                        )
                        platform_results.append(result)
                    except Exception as e:
                        self.logger.error(f"Error scraping URL {url}: {str(e)}")
                        continue
                
                results[platform] = platform_results
                
            except Exception as e:
                self.logger.error(f"Error searching on {platform}: {str(e)}")
                results[platform] = []
                
        return results
    
    def _extract_urls_from_json(self, json_data: Dict[str, Any], platform: str) -> List[str]:
        """Extract URLs from JSON data."""
        urls = []
        
        # Handle different possible JSON structures
        if isinstance(json_data, dict) and "urls" in json_data:
            urls = json_data["urls"]
        elif isinstance(json_data, dict) and "results" in json_data:
            for result in json_data["results"]:
                if isinstance(result, dict) and "url" in result:
                    urls.append(result["url"])
        elif isinstance(json_data, list):
            for item in json_data:
                if isinstance(item, dict) and "url" in item:
                    urls.append(item["url"])
                elif isinstance(item, str) and platform in item and item.startswith("http"):
                    urls.append(item)
        
        return urls
    
    def _extract_urls_from_markdown(self, markdown: str, platform: str) -> List[str]:
        """Extract URLs from markdown content using regex."""
        import re
        
        # Pattern to match URLs in markdown links
        pattern = r'\[.*?\]\((https?://[^)]+)\)'
        urls = re.findall(pattern, markdown)
        
        # Filter URLs to only include those from the specified platform
        urls = [url for url in urls if platform in url]
        
        return urls 