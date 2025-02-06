import logging
from decimal import Decimal
from typing import Any

from alphaswarm.config import Config
from alphaswarm.services.exchanges import DEXFactory, SwapResult
from smolagents import Tool

logger = logging.getLogger(__name__)


class ExecuteTokenSwapTool(Tool):
    """Tool for executing token swaps on supported DEXes."""

    name = "execute_token_swap"
    description = "Execute a token swap on a supported DEX (Uniswap V2/V3 on Ethereum and Base chains)."
    inputs = {
        "token_quote": {
            "type": "string",
            "description": "The quote token symbol (e.g., 'USDC', 'ETH', 'WETH') - the token being sold",
        },
        "token_base": {
            "type": "string",
            "description": "The base token symbol (e.g., 'USDC', 'ETH', 'WETH') - the token being bought",
        },
        "amount": {"type": "number", "description": "The amount of quote token to swap", "required": True},
        "chain": {
            "type": "string",
            "description": "The chain to execute the swap on (e.g., 'ethereum', 'ethereum_sepolia', 'base')",
            "nullable": True,
        },
        "dex_type": {
            "type": "string",
            "description": "The DEX type to use (e.g., 'uniswap_v2', 'uniswap_v3')",
            "nullable": True,
        },
        "slippage_bps": {
            "type": "integer",
            "description": "Maximum slippage in basis points (e.g., 100 = 1%)",
            "nullable": True,
        },
    }
    output_type = "object"

    def __init__(self, config: Config, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.config = config
        # Initialize with None, we'll get the appropriate client when needed

    def forward(
        self,
        *,
        token_quote: str,
        token_base: str,
        amount: Decimal,
        chain: str = "ethereum",
        dex_type: str = "uniswap_v3",
        slippage_bps: int = 100,
    ) -> SwapResult:
        """Execute a token swap."""
        # Create DEX client
        dex_client = DEXFactory.create(dex_name=dex_type, config=self.config, chain=chain)

        # Get wallet address and private key from chain config
        chain_config = self.config.get_chain_config(chain)
        base_token_info = chain_config.get_token_info(token_base)
        quote_token_info = chain_config.get_token_info(token_quote)

        # Log token details
        logger.info(
            f"Swapping {amount} {quote_token_info.symbol} ({quote_token_info.address}) for {base_token_info.symbol} ({base_token_info.address}) on {chain}"
        )

        # Execute swap
        return dex_client.swap(
            base_token=base_token_info,
            quote_token=quote_token_info,
            quote_amount=amount,
            slippage_bps=slippage_bps,
        )
