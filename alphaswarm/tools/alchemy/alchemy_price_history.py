from datetime import datetime, timedelta, timezone
from typing import List, Optional

from alphaswarm.services.alchemy import NETWORKS, AlchemyClient, HistoricalPrice
from smolagents import Tool


class AlchemyPriceHistory(Tool):
    name = "AlchemyPriceHistory"
    description = """Retrieve price history for a given token using Alchemy.
    Alchemy has the following limits for each interval:
    - 2016 samples (7d) for 5m
    - 720 samples (30d) for 1h
    - 365 samples (1y) for 1d
    """
    inputs = {
        "address": {
            "type": "string",
            "description": "Address of the token to retrieve price history for",
        },
        "network": {
            "type": "string",
            "description": "Name of the network hosting the token.",
            "enum": NETWORKS,
        },
        "interval": {
            "type": "string",
            "description": "Time interval between data points. Max samples for each interval: (5m, 2016), (1h, 720), (1d, 365)",
            "enum": ["5m", "1h", "1d"],
        },
        "num_samples": {
            "type": "integer",
            "description": "Number of price samples to retrieve",
            "gt": 0,
            "le": 2016,
        },
    }
    output_type = "object"

    def __init__(self, alchemy_client: Optional[AlchemyClient] = None):
        super().__init__()
        self.client = alchemy_client or AlchemyClient()

    def forward(self, address: str, network: str, interval: str, num_samples: int) -> List[HistoricalPrice]:
        end_time = datetime.now(timezone.utc)
        max_samples = self._max_samples_from_interval(interval)
        samples = min(num_samples, max_samples)

        # Calculate duration based on interval and number of samples
        interval_durations = {
            "5m": timedelta(minutes=5),
            "1h": timedelta(hours=1),
            "1d": timedelta(days=1),
        }
        duration = interval_durations[interval] * (samples - 1)
        start_time = end_time - duration

        return self.client.get_historical_prices_by_address(address, network, start_time, end_time, interval).data

    @staticmethod
    def _max_samples_from_interval(interval: str) -> int:
        interval_limits = {
            "5m": 2016,  # 7 days worth of 5-minute samples
            "1h": 720,   # 30 days worth of hourly samples
            "1d": 365,   # 1 year worth of daily samples
        }
        return interval_limits[interval]
