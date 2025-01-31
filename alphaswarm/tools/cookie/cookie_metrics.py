from datetime import datetime
from enum import Enum
from typing import List, Optional
from dataclasses import dataclass
import logging
import os

import requests
from smolagents import Tool

from alphaswarm.services.cookiefun.cookiefun_client import (
    CookieFunClient,
    AgentMetrics,
    Interval,
    PagedAgentsResponse
)

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

class CookieMetricsClient:
    """Client for interacting with the Cookie.fun API"""
    
    BASE_URL = "https://api.cookie.fun/v2/agents"
    
    def __init__(self):
        self.api_key = os.getenv("COOKIE_FUN_API_KEY")
        if not self.api_key:
            raise ValueError("COOKIE_FUN_API_KEY environment variable not set")
        
        self.headers = {"x-api-key": self.api_key}

    def _parse_agent_response(self, response_data: dict) -> AgentMetrics:
        """Parse API response into AgentMetrics object"""
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
        """Get agent metrics by Twitter username"""
        logger.info(f"Fetching metrics for Twitter username: {username}")
        
        url = f"{self.BASE_URL}/twitterUsername/{username}"
        response = requests.get(url, headers=self.headers, params={"interval": interval})
        response.raise_for_status()
        
        return self._parse_agent_response(response.json())

    def get_agent_by_contract(self, address: str, interval: Interval) -> AgentMetrics:
        """Get agent metrics by contract address"""
        logger.info(f"Fetching metrics for contract address: {address}")
        
        url = f"{self.BASE_URL}/contractAddress/{address}"
        response = requests.get(url, headers=self.headers, params={"interval": interval})
        response.raise_for_status()
        
        return self._parse_agent_response(response.json())

class CookieMetricsByTwitter(Tool):
    name = "CookieMetricsByTwitter"
    description = "Retrieve agent metrics by Twitter username from Cookie.fun"
    inputs = {
        "username": {
            "type": "string",
            "description": "Twitter username of the agent",
        },
        "interval": {
            "type": "string",
            "description": "Time interval for metrics (_3Days or _7Days)",
            "enum": ["_3Days", "_7Days"],
        },
    }
    output_type = "object"

    def __init__(self, client: Optional[CookieFunClient] = None):
        super().__init__()
        self.client = client or CookieFunClient()

    def forward(self, username: str, interval: str) -> AgentMetrics:
        return self.client.get_agent_by_twitter(username, Interval(interval))

class CookieMetricsByContract(Tool):
    name = "CookieMetricsByContract"
    description = "Retrieve agent metrics by contract address from Cookie.fun"
    inputs = {
        "address": {
            "type": "string",
            "description": "Contract address of the agent token",
        },
        "interval": {
            "type": "string",
            "description": "Time interval for metrics (_3Days or _7Days)",
            "enum": ["_3Days", "_7Days"],
        },
    }
    output_type = "object"

    def __init__(self, client: Optional[CookieFunClient] = None):
        super().__init__()
        self.client = client or CookieFunClient()

    def forward(self, address: str, interval: str) -> AgentMetrics:
        return self.client.get_agent_by_contract(address, Interval(interval))

class CookieMetricsPaged(Tool):
    name = "CookieMetricsPaged"
    description = "Retrieve paged list of agents ordered by mindshare from Cookie.fun"
    inputs = {
        "interval": {
            "type": "string",
            "description": "Time interval for metrics (_3Days or _7Days)",
            "enum": ["_3Days", "_7Days"],
        },
        "page": {
            "type": "integer",
            "description": "Page number (starts at 1)",
            "minimum": 1,
        },
        "page_size": {
            "type": "integer",
            "description": "Number of agents per page",
            "minimum": 1,
            "maximum": 25,
        },
    }
    output_type = "object"

    def __init__(self, client: Optional[CookieFunClient] = None):
        super().__init__()
        self.client = client or CookieFunClient()

    def forward(self, interval: str, page: int, page_size: int) -> PagedAgentsResponse:
        return self.client.get_agents_paged(Interval(interval), page, page_size) 