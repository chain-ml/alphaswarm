import logging
from typing import Any

from alphaswarm.config import Config
from alphaswarm.services.exchanges import DEXFactory, SwapResult
from alphaswarm.tools.exchanges.get_token_price_tool import TokenQuote
from smolagents import Tool

logger = logging.getLogger(__name__)


class ExecuteTokenSwapTool(Tool):
    """Tool for executing token swaps on supported DEXes."""

    name = "execute_token_swap"
    description = (
        "Execute a token swap on a supported DEX (Uniswap V2/V3 on Ethereum and Base chains). "
        f"Returns a {SwapResult.__name__} details of the transaction."
    )
    inputs = {
        "quote": {
            "type": "object",
            "description": f"A {TokenQuote.__name__} previously generated",
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

    def forward(
        self,
        *,
        quote: TokenQuote,
        slippage_bps: int = 100,
    ) -> SwapResult:
        """Execute a token swap."""
        # Create DEX client
        dex_client = DEXFactory.create(dex_name=quote.dex, config=self.config, chain=quote.chain)

        inner = quote.quote
        logger.info(
            f"Swapping {inner.amount_in} {inner.token_in.symbol} ({inner.token_in.address}) for {inner.token_out.symbol} ({inner.token_out.address}) on {quote.chain}"
        )

        # Execute swap
        return dex_client.swap(
            quote=quote.quote,
            slippage_bps=slippage_bps,
        )
