from typing import Any

from alphaswarm.config import Config
from smolagents import Tool


class GetTokenAddress(Tool):
    """Tool to get the token address for known token symbols"""

    name = "get_token_address"
    description = "Get the token address for known token symbols"
    inputs = {
        "token_symbol": {
            "type": "string",
            "description": "The token symbol to get the address for",
        },
        "chain": {
            "type": "string",
            "description": "The chain to get the address for. "
            "Must be 'solana' for Solana tokens, 'base' for Base tokens, "
            "'ethereum' for Ethereum tokens, 'ethereum_sepolia' for Ethereum Sepolia tokens.",
            "enum": ["solana", "base", "ethereum", "ethereum_sepolia"],
        },
    }
    output_type = "string"

    def __init__(self, config: Config, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._config = config

    def forward(self, token_symbol: str, chain: str) -> str:
        return self._config.get_chain_config(chain).get_token_info(token_symbol).address
