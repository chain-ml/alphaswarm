from datetime import UTC, datetime
from typing import Any

import requests
from alphaswarm.core.base_tool import AlphaSwarmBaseTool


class GetUsdPrice(AlphaSwarmBaseTool):
    """
    Get the current price of a cryptocurrency in USD using CoinGecko API.
    Returns price and 24h price change percentage.
    """

    inputs = {
        "address": {
            "type": "string",
            "required": True,
            "description": "The contract address of the token",
        },
        "chain": {
            "type": "string",
            "required": True,
            "description": "Blockchain to use. For example, 'solana' for Solana tokens, 'base' for Base tokens, 'ethereum' for Ethereum tokens.",
        },
    }
    output_type = "string"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.base_url = "https://api.coingecko.com/api/v3"
        self.session = requests.Session()

    def __del__(self) -> None:
        """Cleanup the session when the tool is destroyed"""
        self.session.close()

    def forward(self, address: str, chain: str) -> str:
        """
        Fetch current price and 24h change for a given token

        Args:
            address: Contract address of the token
            chain: Blockchain to use
        """
        try:
            # Normalize address to lowercase for consistent comparison
            address = address.lower()

            url = f"{self.base_url}/simple/token_price/{chain}"
            params = {"contract_addresses": address, "vs_currencies": "usd", "include_24hr_change": "true"}

            response = self.session.get(url, params=params, timeout=10)

            if response.status_code != 200:
                return f"Error: Could not fetch price for {address} (Status: {response.status_code})"

            data = response.json()

            if address not in data:
                return f"Error: Token with address '{address}' not found"

            price = data[address]["usd"]
            change_24h = data[address]["usd_24h_change"]

            timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
            return f"[{timestamp}] {address}\n" f"Price: ${price:,.2f}\n" f"24h Change: {change_24h:+.2f}%"

        except requests.RequestException as e:
            return f"Network error: {str(e)}"
        except Exception as e:
            return f"Error fetching price: {str(e)}"
