from datetime import datetime, timedelta, timezone
from typing import Optional

from alphaswarm.services.alchemy import NETWORKS, AlchemyClient, HistoricalPriceByAddress, HistoricalPriceBySymbol
from smolagents import Tool

from alphaswarm.utils.type_description import with_return_type_schema


@with_return_type_schema(HistoricalPriceBySymbol)
class AlchemyPriceHistoryBySymbol(Tool):
    name = "AlchemyPriceHistoryBySymbol"
    description = """Retrieve price history for a given token symbol using Alchemy.
    """
    inputs = {
        "symbol": {
            "type": "string",
            "description": "Symbol/Name of the token to retrieve price history for",
        },
        "interval": {
            "type": "string",
            "description": "Time interval between data points.",
            "enum": ["5m", "1h", "1d"],
        },
        "history": {
            "type": "integer",
            "description": "Number of days to look back price history for. Max history for each interval: (5m, 7d), (1h, 30d), (1d, 365d).",
            "gt": 0,
            "lte": 365,
        },
    }
    output_type = "object"

    def __init__(self, alchemy_client: Optional[AlchemyClient] = None):
        super().__init__()
        self.client = alchemy_client or AlchemyClient()

    def forward(self, symbol: str, interval: str, history: int) -> HistoricalPriceBySymbol:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=history)
        return self.client.get_historical_prices_by_symbol(symbol, start_time, end_time, interval)


@with_return_type_schema(HistoricalPriceByAddress)
class AlchemyPriceHistoryByAddress(Tool):
    name = "AlchemyPriceHistoryByAddress"
    description = """Retrieve price history for a given token address using Alchemy.
    """
    inputs = {
        "address": {
            "type": "string",
            "description": "Hex Address of the token to retrieve price history for",
        },
        "network": {
            "type": "string",
            "description": "Name of the network hosting the token.",
            "enum": NETWORKS,
        },
        "interval": {
            "type": "string",
            "description": "Time interval between data points.",
            "enum": ["5m", "1h", "1d"],
        },
        "history": {
            "type": "integer",
            "description": "Number of days to look back price history for. Max history for each interval: (5m, 7d), (1h, 30d), (1d, 365d).",
            "gt": 0,
            "lte": 365,
        },
    }
    output_type = "object"

    def __init__(self, alchemy_client: Optional[AlchemyClient] = None):
        super().__init__()
        self.client = alchemy_client or AlchemyClient()

    def forward(self, address: str, history: int, interval: str, network: str) -> HistoricalPriceByAddress:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=history)
        return self.client.get_historical_prices_by_address(address, network, start_time, end_time, interval)
