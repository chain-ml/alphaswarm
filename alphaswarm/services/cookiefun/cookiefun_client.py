from enum import Enum
from typing import List, Dict, Optional
from pydantic.dataclasses import dataclass
import logging
import os

import requests
from alphaswarm.services.api_exception import ApiException

# Set up logging
logger = logging.getLogger(__name__)

class Interval(str, Enum):
    THREE_DAYS = "_3Days"
    SEVEN_DAYS = "_7Days"

@dataclass
class Contract:
    chain: int
    contractAddress: str

@dataclass
class Tweet:
    tweetUrl: str
    tweetAuthorProfileImageUrl: str
    tweetAuthorDisplayName: str
    smartEngagementPoints: int
    impressionsCount: int

@dataclass
class AgentMetrics:
    agentName: str
    contracts: List[Contract]
    twitterUsernames: List[str]
    mindshare: float
    mindshareDeltaPercent: float
    marketCap: float
    marketCapDeltaPercent: float
    price: float
    priceDeltaPercent: float
    liquidity: float
    volume24Hours: float
    volume24HoursDeltaPercent: float
    holdersCount: int
    holdersCountDeltaPercent: float
    averageImpressionsCount: float
    averageImpressionsCountDeltaPercent: float
    averageEngagementsCount: float
    averageEngagementsCountDeltaPercent: float
    followersCount: int
    smartFollowersCount: int
    topTweets: List[Tweet]

@dataclass
class PagedAgentsResponse:
    """Response from the paged agents endpoint"""
    data: List[AgentMetrics]
    currentPage: int
    totalPages: int
    totalCount: int

class CookieFunClient:
    """Client for interacting with the Cookie.fun API"""
    
    BASE_URL = "https://api.cookie.fun/v2/agents"
    
    def __init__(self, base_url: str = BASE_URL, api_key: Optional[str] = None, **kwargs):
        """Initialize the Cookie.fun API client
        
        Raises:
            ValueError: If COOKIE_FUN_API_KEY environment variable is not set
        """
        self.base_url = base_url
        self.api_key = api_key or os.getenv("COOKIE_FUN_API_KEY")
        if not self.api_key:
            raise ValueError("COOKIE_FUN_API_KEY environment variable not set")
        
        self.headers = {"x-api-key": self.api_key}
        logger.debug("CookieFun client initialized")

    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make API request to Cookie.fun
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            Dict: API response data
            
        Raises:
            ApiException: If API request fails
            Exception: For other errors
        """
        url = f"{self.BASE_URL}{endpoint}"

        try:
            response = requests.get(url, headers=self.headers, params=params)

            if response.status_code >= 400:
                raise ApiException(response)

            return response.json()

        except Exception:
            logger.exception("Error fetching data from Cookie.fun")
            raise

    def _parse_agent_response(self, response_data: dict) -> AgentMetrics:
        """Parse API response into AgentMetrics object
        
        Args:
            response_data: Raw API response dictionary
            
        Returns:
            AgentMetrics: Parsed metrics object
        """
        logger.debug(f"Parsing agent response: {response_data}")
        
        data = response_data["ok"]
        return AgentMetrics(**data)

    def get_agent_by_twitter(self, username: str, interval: Interval) -> AgentMetrics:
        """Get agent metrics by Twitter username
        
        Args:
            username: Twitter username of the agent
            interval: Time interval for metrics
            
        Returns:
            AgentMetrics: Agent metrics data
            
        Raises:
            ApiException: If API request fails
        """
        logger.info(f"Fetching metrics for Twitter username: {username}")
        
        response = self._make_request(
            f"/twitterUsername/{username}",
            params={"interval": interval}
        )
        return self._parse_agent_response(response)

    def get_agent_by_contract(self, address: str, interval: Interval) -> AgentMetrics:
        """Get agent metrics by contract address
        
        Args:
            address: Contract address of the agent token
            interval: Time interval for metrics
            
        Returns:
            AgentMetrics: Agent metrics data
            
        Raises:
            ApiException: If API request fails
        """
        logger.info(f"Fetching metrics for contract address: {address}")
        
        response = self._make_request(
            f"/contractAddress/{address}",
            params={"interval": interval}
        )
        return self._parse_agent_response(response)

    def get_agents_paged(self, interval: Interval, page: int, page_size: int) -> PagedAgentsResponse:
        """Get paged list of AI agents ordered by mindshare
        
        Args:
            interval: Time interval for metrics
            page: Page number (starts at 1)
            page_size: Number of agents per page (between 1 and 25)
            
        Returns:
            PagedAgentsResponse: Paged list of agent metrics
            
        Raises:
            ValueError: If page_size is not between 1 and 25
            ApiException: If API request fails
        """
        if not 1 <= page_size <= 25:
            raise ValueError("page_size must be between 1 and 25")
        
        logger.info(f"Fetching agents page {page} with size {page_size}")
        
        response = self._make_request(
            "/agentsPaged",
            params={
                "interval": interval,
                "page": page,
                "pageSize": page_size
            }
        )
        
        data = response["ok"]
        return PagedAgentsResponse(
            data=[AgentMetrics(**agent) for agent in data["data"]],
            currentPage=data["currentPage"],
            totalPages=data["totalPages"],
            totalCount=data["totalCount"]
        ) 