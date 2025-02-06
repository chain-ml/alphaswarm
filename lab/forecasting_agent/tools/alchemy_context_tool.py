from datetime import datetime, timedelta, timezone

import pandas as pd
from alphaswarm.services.alchemy import AlchemyClient, HistoricalPriceBySymbol
from smolagents import Tool


class AlchemyContextTool(Tool):
    name = "get_alchemy_context"
    description = """Get summary of the historical price data for a given token.
    Returns three tables in the string format:
    - price for the last 30 days with 1 day granularity
    - price for the last 24 hours with 1 hour granularity
    - price for the last 1 hour with 5 minute granularity
    """
    inputs = {
        "symbol": {
            "type": "string",
            "description": "Symbol/Name of the token to retrieve price history for",
        }
    }
    output_type = "string"

    def forward(self, symbol: str) -> str:
        return self.get_alchemy_context(symbol)

    @classmethod
    def get_alchemy_context(cls, symbol: str) -> str:
        client = AlchemyClient()
        end_date = datetime.now(timezone.utc)

        start_date_for_1d = end_date - timedelta(days=30)
        history_1d = client.get_historical_prices_by_symbol(symbol, start_date_for_1d, end_date, "1d")

        start_date_for_1h = end_date - timedelta(hours=24)
        history_1h = client.get_historical_prices_by_symbol(symbol, start_date_for_1h, end_date, "1h")

        start_date_for_1m = end_date - timedelta(hours=1)
        history_1m = client.get_historical_prices_by_symbol(symbol, start_date_for_1m, end_date, "5m")

        return "\n".join(
            [
                f"Current date and time: {end_date.strftime('%Y-%m-%d %H:%M:%S')}",
                "Historical price data for the last 30 days with 1 day granularity:",
                cls.historical_prices_to_str(history_1d),
                "Historical price data for the last 24 hours with 1 hour granularity:",
                cls.historical_prices_to_str(history_1h),
                "Historical price data for the last 1 hour with 5 minute granularity:",
                cls.historical_prices_to_str(history_1m),
            ]
        )

    @staticmethod
    def historical_prices_to_str(history: HistoricalPriceBySymbol) -> str:
        """Format HistoricalPriceBySymbol as csv data."""
        df = pd.DataFrame([(price.timestamp, price.value) for price in history.data], columns=["timestamp", "value"])
        df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        return df.to_csv(index=False)
