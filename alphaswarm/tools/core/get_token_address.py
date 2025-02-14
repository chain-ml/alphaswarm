from typing import Any

from alphaswarm.config import Config
from alphaswarm.core.tool import AlphaSwarmTool


class GetTokenAddress(AlphaSwarmTool):
    """Get the token address for known token symbols"""

    inputs = {
        "token_symbol": {
            "type": "string",
            "description": "The token symbol to get the address for",
        },
        "chain": {
            "type": "string",
            "description": "The chain to get the address for",
        },
    }

    def __init__(self, config: Config, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._config = config

    def forward(self, token_symbol: str, chain: str) -> str:
        return self._config.get_chain_config(chain).get_token_info(token_symbol).address
