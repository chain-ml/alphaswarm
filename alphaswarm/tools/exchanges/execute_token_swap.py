import logging
from typing import Any

from alphaswarm.config import Config
from alphaswarm.core.tool import AlphaSwarmTool
from alphaswarm.services.exchanges import DEXFactory, SwapResult

from .get_token_price import TokenQuote

logger = logging.getLogger(__name__)


class ExecuteTokenSwap(AlphaSwarmTool):
    """
    Execute a token swap on a supported DEX (Uniswap V2/V3 on Ethereum and Base chains).
    Returns a SwapResult details of the transaction.
    """

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
            f"Swapping {inner.amount_in} {inner.token_in.symbol} ({inner.token_in.address}) "
            f"for {inner.token_out.symbol} ({inner.token_out.address}) on {quote.chain}"
        )

        # Execute swap
        return dex_client.swap(
            quote=quote.quote,
            slippage_bps=slippage_bps,
        )
