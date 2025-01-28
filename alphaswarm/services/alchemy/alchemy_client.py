import logging
import os
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime, timezone
import requests
from pydantic.dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class HistoricalTokenPrice:
    value: Decimal
    timestamp: datetime

class AlchemyClient:
    """Alchemy API data source for historical token prices"""

    BASE_URL = "https://api.g.alchemy.com/prices/v1"

    def __init__(
        self,
        base_url: str = BASE_URL,
        endpoints: Optional[Dict] = None,
        metrics: Optional[List] = None,
        timeframes: Optional[List] = None,
        rate_limits: Optional[Dict] = None,
        api_key: Optional[str] = None,
        **kwargs,
    ):
        """Initialize Alchemy data source"""
        self.base_url = base_url
        self.api_key = api_key or os.getenv("ALCHEMY_API_KEY")
        if not self.api_key:
            raise ValueError("ALCHEMY_API_KEY not found in environment variables")

        self.endpoints = endpoints or {
            "historical": "/{api_key}/tokens/historical",
        }

        self.supported_metrics = metrics or ["price_usd", "historical_price"]

        self.supported_timeframes = timeframes or ["1h", "1d", "1w", "1m"]

        # Map our timeframes to Alchemy intervals
        self.timeframe_mapping = {"1h": "1h", "1d": "1d", "1w": "1w", "1m": "30d"}

    def _make_request(self, endpoint: str, data: Dict) -> Dict:
        """Make API request to Alchemy"""
        url = f"{self.base_url}{endpoint.format(api_key=self.api_key)}"

        try:
            response = requests.post(
                url, json=data, headers={"accept": "application/json", "content-type": "application/json"}
            )

            if response.status_code == 429:
                logger.error("Alchemy API rate limit exceeded")
                raise RuntimeError("Rate limit exceeded")

            if response.status_code == 404:
                logger.error(f"Token not found: {data.get('symbol') or data.get('contractAddress')}")
                raise RuntimeError("Token not found")

            if response.status_code != 200:
                logger.error(f"Alchemy API error: {response.status_code}")
                raise RuntimeError(f"API error: {response.status_code}")

            return response.json()

        except Exception:
            logger.exception(f"Error fetching data from Alchemy")
            raise

    def get_historical_prices(
        self,
        token: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = "1d",
        chain: Optional[str] = None,
    ) -> List[HistoricalTokenPrice]:
        """
        Get historical price data for a token

        Args:
            token: Token symbol or contract address
            start_time: Start time for historical data
            end_time: End time for historical data
            interval: Time interval (5m, 1h, 1d)
            chain: Optional chain ID if using contract address
        """
        # Convert times to ISO format
        start_iso = start_time.astimezone(timezone.utc).isoformat()
        end_iso = end_time.astimezone(timezone.utc).isoformat()

        # Prepare request data
        data = {"startTime": start_iso, "endTime": end_iso, "interval": interval}

        # Add either symbol or contract address
        if len(token) < 10:  # Assume it's a symbol
            data["symbol"] = token
        else:  # Assume it's a contract address
            data["contractAddress"] = token
            if chain:
                data["chainId"] = chain

        response = self._make_request(self.endpoints["historical"], data)
        return [HistoricalTokenPrice(**values) for values in response["data"]]
