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
            "description": "Address of the token to retrieve price history for",
        },
        "network": {
            "type": "string",
            "description": "Name of the network hosting the token. Only relevant is a token address is used",
            "nullable": True,
            "enum": NETWORKS,
        },
        "history": {
            "type": "integer",
            "description": "Number of days to look back price history for",
            "gt": 0,
            "lte": 365,
        },
    }
    output_type = "object"

    def __init__(self, alchemy_client: AlchemyClient):
        super().__init__()
        self.client = alchemy_client

    def forward(self, address_or_symbol: str, history: int, network: Optional[str] = None) -> List[HistoricalPrice]:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=history)
        interval = self._interval_from_history(history)
        if network is not None:
            return self.client.get_historical_prices_by_address(
                address_or_symbol, network, start_time, end_time, interval
            ).data
        else:
            return self.client.get_historical_prices_by_symbol(address_or_symbol, start_time, end_time, interval).data

    @staticmethod
    def _interval_from_history(history: int) -> str:
        if history <= 7:
            return "5m"
        if history <= 30:
            return "1h"
        return "1d"
