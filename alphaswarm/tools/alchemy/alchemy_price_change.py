from datetime import datetime
from decimal import Decimal
from typing import Optional

from alphaswarm.services.alchemy import AlchemyClient
from alphaswarm.tools.alchemy import AlchemyPriceHistoryByAddress
from pydantic import BaseModel
from smolagents import Tool


class TokenPriceChange(BaseModel):
    token_address: str
    network: str
    start_time: datetime
    end_time: datetime
    start_price: float
    end_price: float
    percent_change: float
    n_samples: int
    frequency: str


class TokenPriceChangeCalculator(Tool):
    name = "TokenPriceChangeCalculator"
    description = "Calculate the percentage price change for a token over a specified number of samples and frequency"
    inputs = {
        "token_address": {
            "type": "string",
            "description": "The token address to analyze",
        },
        "frequency": {
            "type": "string",
            "description": "Time interval between data points",
            "enum": ["5m", "1h", "1d"],
        },
        "n_samples": {
            "type": "integer",
            "description": "Number of samples to analyze (must be >= 2)",
            "minimum": 2,
        },
        "network": {
            "type": "string",
            "description": "Network where the token exists (e.g. eth-mainnet, base-mainnet)",
            "default": "eth-mainnet",
            "nullable": True,
        },
    }
    output_type = "object"

    def __init__(self, alchemy_client: Optional[AlchemyClient] = None):
        super().__init__()
        self.price_history_tool = AlchemyPriceHistoryByAddress(alchemy_client)

    def _calculate_percent_change(self, start_price: Decimal, end_price: Decimal) -> float:
        return float((end_price - start_price) / start_price * 100)

    def forward(
        self, token_address: str, frequency: str, n_samples: int, network: str = "eth-mainnet"
    ) -> TokenPriceChange:
        # Calculate the required history in days based on frequency and n_samples
        interval_to_minutes = {"5m": 5, "1h": 60, "1d": 1440}
        minutes_needed = interval_to_minutes[frequency] * n_samples
        days_needed = (minutes_needed // 1440) + 1  # Round up to nearest day

        # Use the existing price history tool
        price_history = self.price_history_tool.forward(
            address=token_address, network=network, interval=frequency, history=days_needed
        )

        # Ensure we have enough data points
        prices = price_history.data[-n_samples:]  # Get the most recent n_samples
        if len(prices) < n_samples:
            raise ValueError(f"Requested {n_samples} samples but only got {len(prices)}")

        # Calculate percent changes
        start_price = prices[0].value
        end_price = prices[-1].value
        percent_change = self._calculate_percent_change(start_price, end_price)

        return TokenPriceChange(
            token_address=token_address,
            network=network,
            start_time=prices[0].timestamp,
            end_time=prices[-1].timestamp,
            start_price=float(start_price),
            end_price=float(end_price),
            percent_change=percent_change,
            n_samples=n_samples,
            frequency=frequency,
        )
