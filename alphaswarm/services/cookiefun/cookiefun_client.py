import logging
import os
from enum import Enum
from typing import Dict, List, Optional

import requests
from alphaswarm.config import Config
from alphaswarm.services.api_exception import ApiException
from pydantic import Field
from pydantic.dataclasses import dataclass

# Set up logging
logger = logging.getLogger(__name__)


class Interval(str, Enum):
    THREE_DAYS = "_3Days"
    SEVEN_DAYS = "_7Days"


@dataclass
class Contract:
    chain: int  # Required field first
    contract_address: str = Field(alias="contractAddress")  # Field with alias after


@dataclass
class Tweet:
    # All fields have aliases, but we still need to maintain a logical order
    tweet_url: str = Field(alias="tweetUrl")
    tweet_author_profile_image_url: str = Field(alias="tweetAuthorProfileImageUrl")
    tweet_author_display_name: str = Field(alias="tweetAuthorDisplayName")
    smart_engagement_points: int = Field(alias="smartEngagementPoints")
    impressions_count: int = Field(alias="impressionsCount")


@dataclass
class AgentMetrics:
    # Required fields (no defaults) first
    contracts: List[Contract]
    mindshare: float
    price: float
    liquidity: float
    
    # Optional/fields with defaults after
    agent_name: str = Field(alias="agentName")
    twitter_usernames: List[str] = Field(alias="twitterUsernames")
    mindshare_delta_percent: float = Field(alias="mindshareDeltaPercent")
    market_cap: float = Field(alias="marketCap")
    market_cap_delta_percent: float = Field(alias="marketCapDeltaPercent")
    price_delta_percent: float = Field(alias="priceDeltaPercent")
    volume_24_hours: float = Field(alias="volume24Hours")
    volume_24_hours_delta_percent: float = Field(alias="volume24HoursDeltaPercent")
    holders_count: int = Field(alias="holdersCount")
    holders_count_delta_percent: float = Field(alias="holdersCountDeltaPercent")
    average_impressions_count: float = Field(alias="averageImpressionsCount")
    average_impressions_count_delta_percent: float = Field(alias="averageImpressionsCountDeltaPercent")
    average_engagements_count: float = Field(alias="averageEngagementsCount")
    average_engagements_count_delta_percent: float = Field(alias="averageEngagementsCountDeltaPercent")
    followers_count: int = Field(alias="followersCount")
    smart_followers_count: int = Field(alias="smartFollowersCount")
    top_tweets: List[Tweet] = Field(alias="topTweets")


@dataclass
class PagedAgentsResponse:
    """Response from the paged agents endpoint"""
    data: List[AgentMetrics]  # Required field first
    current_page: int = Field(alias="currentPage")
    total_pages: int = Field(alias="totalPages")
    total_count: int = Field(alias="totalCount")


class CookieFunClient:
    """Client for interacting with the Cookie.fun API"""

    BASE_URL = "https://api.cookie.fun/v2/agents"

    def __init__(
        self, base_url: str = BASE_URL, api_key: Optional[str] = None, config: Optional[Config] = None, **kwargs
    ):
        """Initialize the Cookie.fun API client

        Args:
            base_url: Base URL for the API
            api_key: API key for authentication
            config: Config instance for token lookups

        Raises:
            ValueError: If COOKIE_FUN_API_KEY environment variable is not set
        """
        self.base_url = base_url
        self.api_key = api_key or os.getenv("COOKIE_FUN_API_KEY")
        if not self.api_key:
            raise ValueError("COOKIE_FUN_API_KEY environment variable not set")

        self.headers = {"x-api-key": self.api_key}
        self.config = config or Config()
        logger.debug("CookieFun client initialized")

    def _get_token_address(self, symbol: str) -> tuple[Optional[str], Optional[str]]:
        """Get token address and chain from symbol using config

        Args:
            symbol: Token symbol to look up

        Returns:
            tuple: (token_address, chain) if found, (None, None) if not found

        Raises:
            Exception: If there's an error during lookup
        """
        try:
            # Get all supported chains from config
            supported_chains = self.config.get_supported_networks()

            # Search through each chain for the token
            for chain in supported_chains:
                chain_config = self.config.get_chain_config(chain)
                token_info = chain_config.get_token_info_or_none(symbol)
                if token_info:
                    logger.debug(f"Found token {symbol} on chain {chain}")
                    return token_info.address, chain

            logger.warning(f"Token {symbol} not found in any chain config")
            raise ValueError(f"Token {symbol} not found in any chain config")

        except Exception:
            logger.exception(f"Failed to find token address for {symbol}")
            raise ValueError(f"Failed to find token address for {symbol}")

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

        response = self._make_request(f"/twitterUsername/{username}", params={"interval": interval})
        return self._parse_agent_response(response)

    def get_agent_by_contract(self, address_or_symbol: str, interval: Interval, chain: str = None) -> AgentMetrics:
        """Get agent metrics by contract address or symbol

        Args:
            address_or_symbol: Contract address or token symbol
            interval: Time interval for metrics
            chain: Optional chain override (not needed for symbols as they are unique per chain)

        Returns:
            AgentMetrics: Agent metrics data

        Raises:
            ApiException: If API request fails
            ValueError: If symbol not found in any chain
        """
        # If input looks like an address, use it directly with provided chain
        if address_or_symbol.startswith("0x") or address_or_symbol.startswith("1"):
            address = address_or_symbol
        else:
            # Try to look up symbol
            address, detected_chain = self._get_token_address(address_or_symbol)
            if not address:
                raise ValueError(f"Could not find address for token {address_or_symbol} in any chain")

            # Use detected chain unless explicitly overridden
            chain = chain or detected_chain
            logger.info(f"Resolved symbol {address_or_symbol} to address {address} on chain {chain}")

        logger.info(f"Fetching metrics for contract address: {address}")

        response = self._make_request(f"/contractAddress/{address}", params={"interval": interval})
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
            "/agentsPaged", params={"interval": interval, "page": page, "pageSize": page_size}
        )

        return PagedAgentsResponse(**response["ok"])
