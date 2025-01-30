from datetime import datetime, timedelta, timezone
from typing import List, Optional

from alphaswarm.services.alchemy import NETWORKS, AlchemyClient, HistoricalPrice
from smolagents import Tool


class AlchemyPriceHistory(Tool):
    name = "AlchemyPriceHistory"
    description = "Retrieve price history for a given token using Alchemy"
    inputs = {
        "address_or_symbol": {
            "type": "string",
            "description": "Address or symbol of the token to retrieve price history for",
        },
        "network": {
            "type": "string",
            "description": "Name of the network hosting the token. Provide ONLY if a token address is used",
            "nullable": True,
            "enum": NETWORKS,
        },
        "interval": {
            "type": "string",
            "description": "Time interval between data points. Max history for each interval: (5m, 7d), (1h, 30d), (1d, 1yr)",
            "enum": ["5m", "1h", "1d"],
        },
        "history": {
            "type": "integer",
            "description": "Number of days to look back price history for",
            "gt": 0,
            "lte": 365,
        },
    }
    output_type = "object"

    def __init__(self, alchemy_client: Optional[AlchemyClient] = None):
        super().__init__()
        self.client = alchemy_client or AlchemyClient()

    def forward(
        self, address_or_symbol: str, interval: str, history: int, network: Optional[str] = None
    ) -> List[HistoricalPrice]:
        end_time = datetime.now(timezone.utc)
        max_history = self._max_history_from_interval(interval)
        history = min(history, max_history)
        start_time = end_time - timedelta(days=history)

        if network is not None:
            return self.client.get_historical_prices_by_address(
                address_or_symbol, network, start_time, end_time, interval
            ).data
        else:
            return self.client.get_historical_prices_by_symbol(address_or_symbol, start_time, end_time, interval).data

    @staticmethod
    def _max_history_from_interval(interval: str) -> int:
        interval_limits = {
            "5m": 7,  # 7 days
            "1h": 30,  # 30 days
            "1d": 365,  # 1 year
        }
        return interval_limits[interval]
