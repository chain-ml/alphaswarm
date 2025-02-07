from datetime import UTC, datetime
from typing import Any

import requests
from smolagents import Tool


class PriceTool(Tool):
    """Tool for getting current price of crypto tokens using CoinGecko API"""

    name = "price_tool"
    description = """
    Get the current price of a cryptocurrency in USD.
    Supports major tokens like 'bitcoin', 'ethereum', etc.
    Returns price and 24h price change percentage.
    """
    inputs = {
        "token_id": {
            "type": "string",
            "required": True,
            "description": "The CoinGecko token ID (e.g., 'bitcoin', 'ethereum')",
        }
    }
    output_type = "object"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.base_url = "https://api.coingecko.com/api/v3"
        self.session = requests.Session()

    def __del__(self) -> None:
        """Cleanup the session when the tool is destroyed"""
        self.session.close()

    def forward(self, token_id: str) -> str:
        """
        Fetch current price and 24h change for a given token

        Args:
            token_id: CoinGecko token ID (e.g., 'bitcoin', 'ethereum')
        """
        try:
            url = f"{self.base_url}/simple/price"
            params = {"ids": token_id, "vs_currencies": "usd", "include_24hr_change": "true"}

            response = self.session.get(url, params=params, timeout=10)

            if response.status_code != 200:
                return f"Error: Could not fetch price for {token_id} (Status: {response.status_code})"

            data = response.json()

            if token_id not in data:
                return f"Error: Token '{token_id}' not found"

            price = data[token_id]["usd"]
            change_24h = data[token_id]["usd_24h_change"]

            timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
            return f"[{timestamp}] {token_id.upper()}\n" f"Price: ${price:,.2f}\n" f"24h Change: {change_24h:+.2f}%"

        except requests.RequestException as e:
            return f"Network error: {str(e)}"
        except Exception as e:
            return f"Error fetching price: {str(e)}"
