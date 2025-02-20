from datetime import datetime, timedelta, timezone
from typing import Optional

from alphaswarm.core.tool import AlphaSwarmToolBase
from alphaswarm.services.alchemy import AlchemyClient, HistoricalPriceByAddress, HistoricalPriceBySymbol


class GetAlchemyPriceHistoryBySymbol(AlphaSwarmToolBase):
    """Retrieve price history for a given token symbol using Alchemy API"""

    def __init__(self, alchemy_client: Optional[AlchemyClient] = None) -> None:
        super().__init__()
        self.client = alchemy_client or AlchemyClient.from_env()

    def forward(self, symbol: str, interval: str, history: int) -> HistoricalPriceBySymbol:
        """
        Args:
            symbol: Symbol/Name of the token to retrieve price history for
            interval: Time interval between data points, one of "5m", "1h", "1d".
            history: Number of days to look back price history for. Max history for each interval - (5m, 7d), (1h, 30d), (1d, 365d).
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=history)
        return self.client.get_historical_prices_by_symbol(symbol, start_time, end_time, interval)


class GetAlchemyPriceHistoryByAddress(AlphaSwarmToolBase):
    """Retrieve price history for a given token address using Alchemy API"""

    def __init__(self, alchemy_client: Optional[AlchemyClient] = None) -> None:
        super().__init__()
        self.client = alchemy_client or AlchemyClient.from_env()

    def forward(self, address: str, history: int, interval: str, network: str) -> HistoricalPriceByAddress:
        """
        Args:
            address: Hex Address of the token to retrieve price history for
            history: Number of days to look back price history for. Max history for each interval - (5m, 7d), (1h, 30d), (1d, 365d).
            interval: Time interval between data points, one of "5m", "1h", "1d".
            network: Name of the network hosting the token.
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=history)
        return self.client.get_historical_prices_by_address(
            address=address, network=network, start_time=start_time, end_time=end_time, interval=interval
        )
