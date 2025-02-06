from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Final, List

import requests
from alphaswarm.services.api_exception import ApiException
from pydantic.dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HistoricalPrice:
    value: Decimal
    timestamp: datetime


@dataclass
class HistoricalPriceBySymbol:
    symbol: str
    data: List[HistoricalPrice]


@dataclass
class HistoricalPriceByAddress:
    address: str
    network: str
    data: List[HistoricalPrice]


NETWORKS = ["eth-mainnet", "base-mainnet", "solana-mainnet", "eth-sepolia", "base-sepolia", "solana-devnet"]


class AlchemyClient:
    """Alchemy API data source for historical token prices"""

    DEFAULT_BASE_URL: Final[str] = "https://api.g.alchemy.com"
    ENDPOINT_TOKENS_HISTORICAL: Final[str] = "/prices/v1/{api_key}/tokens/historical"

    def __init__(self, *, api_key: str, base_url: str = DEFAULT_BASE_URL) -> None:
        """Initialize Alchemy data source"""
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {"accept": "application/json", "content-type": "application/json"}

    def _make_request(self, endpoint: str, data: Dict) -> Dict:
        """Make API request to Alchemy"""
        url = f"{self.base_url}{endpoint.format(api_key=self.api_key)}"

        try:
            response = requests.post(url, json=data, headers=self.headers)

            if response.status_code >= 400:
                raise ApiException(response)

            return response.json()

        except Exception:
            logger.exception("Error fetching data from Alchemy")
            raise

    def get_historical_prices_by_symbol(
        self, symbol: str, start_time: datetime, end_time: datetime, interval: str
    ) -> HistoricalPriceBySymbol:
        """
        Get historical price data for a token

        Args:
            symbol: Token symbol or contract address
            start_time: Start time for historical data
            end_time: End time for historical data
            interval: Time interval (5m, 1h, 1d)
        """
        start_iso = start_time.astimezone(timezone.utc).isoformat()
        end_iso = end_time.astimezone(timezone.utc).isoformat()

        # Prepare request data
        data = {"symbol": symbol, "startTime": start_iso, "endTime": end_iso, "interval": interval}
        response = self._make_request(self.ENDPOINT_TOKENS_HISTORICAL, data)
        return HistoricalPriceBySymbol(**response)

    def get_historical_prices_by_address(
        self,
        *,
        address: str,
        network: str,
        start_time: datetime,
        end_time: datetime,
        interval: str,
    ) -> HistoricalPriceByAddress:
        """
        Get historical price data for a token

        Args:
            address: Token address (e.g. '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48')
            network: Network identifier (e.g. 'eth-mainnet')
            start_time: Start time for historical data
            end_time: End time for historical data
            interval: Time interval (5m, 1h, 1d)
        """
        # Convert times to ISO format
        start_iso = start_time.astimezone(timezone.utc).isoformat()
        end_iso = end_time.astimezone(timezone.utc).isoformat()

        # Prepare request data
        data = {
            "address": address,
            "network": network,
            "startTime": start_iso,
            "endTime": end_iso,
            "interval": interval,
        }
        response = self._make_request(self.ENDPOINT_TOKENS_HISTORICAL, data)
        return HistoricalPriceByAddress(**response)

    @staticmethod
    def from_env() -> AlchemyClient:
        api_key = os.getenv("ALCHEMY_API_KEY")
        if not api_key:
            raise RuntimeError("ALCHEMY_API_KEY not found in environment variables")

        return AlchemyClient(api_key=api_key)
