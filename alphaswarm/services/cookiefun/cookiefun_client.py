from datetime import datetime
from enum import Enum
from typing import List
from pydantic.dataclasses import dataclass
import logging
import os

import requests

# Set up logging
logger = logging.getLogger(__name__)

class Interval(str, Enum):
    THREE_DAYS = "_3Days"
    SEVEN_DAYS = "_7Days"

@dataclass
class Contract:
    chain: int
    contract_address: str

@dataclass
class Tweet:
    tweet_url: str
    tweet_author_profile_image_url: str
    tweet_author_display_name: str
    smart_engagement_points: int
    impressions_count: int

@dataclass
class AgentMetrics:
    agent_name: str
    contracts: List[Contract]
    twitter_usernames: List[str]
    mindshare: float
    mindshare_delta_percent: float
    market_cap: float
    market_cap_delta_percent: float
    price: float
    price_delta_percent: float
    liquidity: float
    volume_24_hours: float
    volume_24_hours_delta_percent: float
    holders_count: int
    holders_count_delta_percent: float
    average_impressions_count: float
    average_impressions_count_delta_percent: float
    average_engagements_count: float
    average_engagements_count_delta_percent: float
    followers_count: int
    smart_followers_count: int
    top_tweets: List[Tweet]

@dataclass
class PagedAgentsResponse:
    """Response from the paged agents endpoint"""
    data: List[AgentMetrics]
    current_page: int
    total_pages: int
    total_count: int

class CookieFunClient:
    """Client for interacting with the Cookie.fun API"""
    
    BASE_URL = "https://api.cookie.fun/v2/agents"
    
    def __init__(self):
        """Initialize the Cookie.fun API client
        
        Raises:
            ValueError: If COOKIE_FUN_API_KEY environment variable is not set
        """
        self.api_key = os.getenv("COOKIE_FUN_API_KEY")
        if not self.api_key:
            raise ValueError("COOKIE_FUN_API_KEY environment variable not set")
        
        self.headers = {"x-api-key": self.api_key}
        logger.debug("CookieFun client initialized")

    def _parse_agent_response(self, response_data: dict) -> AgentMetrics:
        """Parse API response into AgentMetrics object
        
        Args:
            response_data: Raw API response dictionary
            
        Returns:
            AgentMetrics: Parsed metrics object
        """
        logger.debug(f"Parsing agent response: {response_data}")
        
        data = response_data["ok"]
        return AgentMetrics(
            agent_name=data["agentName"],
            contracts=[Contract(**c) for c in data["contracts"]],
            twitter_usernames=data["twitterUsernames"],
            mindshare=data["mindshare"],
            mindshare_delta_percent=data["mindshareDeltaPercent"],
            market_cap=data["marketCap"],
            market_cap_delta_percent=data["marketCapDeltaPercent"],
            price=data["price"],
            price_delta_percent=data["priceDeltaPercent"],
            liquidity=data["liquidity"],
            volume_24_hours=data["volume24Hours"],
            volume_24_hours_delta_percent=data["volume24HoursDeltaPercent"],
            holders_count=data["holdersCount"],
            holders_count_delta_percent=data["holdersCountDeltaPercent"],
            average_impressions_count=data["averageImpressionsCount"],
            average_impressions_count_delta_percent=data["averageImpressionsCountDeltaPercent"],
            average_engagements_count=data["averageEngagementsCount"],
            average_engagements_count_delta_percent=data["averageEngagementsCountDeltaPercent"],
            followers_count=data["followersCount"],
            smart_followers_count=data["smartFollowersCount"],
            top_tweets=[Tweet(**t) for t in data["topTweets"]]
        )

    def get_agent_by_twitter(self, username: str, interval: Interval) -> AgentMetrics:
        """Get agent metrics by Twitter username
        
        Args:
            username: Twitter username of the agent
            interval: Time interval for metrics
            
        Returns:
            AgentMetrics: Agent metrics data
            
        Raises:
            requests.exceptions.RequestException: If API request fails
        """
        logger.info(f"Fetching metrics for Twitter username: {username}")
        
        url = f"{self.BASE_URL}/twitterUsername/{username}"
        response = requests.get(url, headers=self.headers, params={"interval": interval})
        response.raise_for_status()
        
        return self._parse_agent_response(response.json())

    def get_agent_by_contract(self, address: str, interval: Interval) -> AgentMetrics:
        """Get agent metrics by contract address
        
        Args:
            address: Contract address of the agent token
            interval: Time interval for metrics
            
        Returns:
            AgentMetrics: Agent metrics data
            
        Raises:
            requests.exceptions.RequestException: If API request fails
        """
        logger.info(f"Fetching metrics for contract address: {address}")
        
        url = f"{self.BASE_URL}/contractAddress/{address}"
        response = requests.get(url, headers=self.headers, params={"interval": interval})
        response.raise_for_status()
        
        return self._parse_agent_response(response.json())

    def get_agents_paged(self, interval: Interval, page: int, page_size: int) -> PagedAgentsResponse:
        """Get paged list of agents ordered by mindshare
        
        Args:
            interval: Time interval for metrics
            page: Page number (starts at 1)
            page_size: Number of agents per page (between 1 and 25)
            
        Returns:
            PagedAgentsResponse: Paged list of agent metrics
            
        Raises:
            ValueError: If page_size is not between 1 and 25
            requests.exceptions.RequestException: If API request fails
        """
        if not 1 <= page_size <= 25:
            raise ValueError("page_size must be between 1 and 25")
        
        logger.info(f"Fetching agents page {page} with size {page_size}")
        
        url = f"{self.BASE_URL}/agentsPaged"
        params = {
            "interval": interval,
            "page": page,
            "pageSize": page_size
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        
        data = response.json()["ok"]
        return PagedAgentsResponse(
            data=[self._parse_agent_response({"ok": agent}) for agent in data["data"]],
            current_page=data["currentPage"],
            total_pages=data["totalPages"],
            total_count=data["totalCount"]
        ) 