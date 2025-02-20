import logging
from typing import Any

from alphaswarm.config import Config
from alphaswarm.core.tool import AlphaSwarmToolBase
from alphaswarm.services.exchanges import DEXFactory, SwapResult

from .get_token_price import TokenQuote

logger = logging.getLogger(__name__)


class ExecuteTokenSwap(AlphaSwarmToolBase):
    """Execute a token swap on a supported DEX (Uniswap V2/V3 on Ethereum and Base chains)."""

    def __init__(self, config: Config, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.config = config

    def forward(self, quote: TokenQuote, slippage_bps: int = 100) -> SwapResult:
        """
        Execute a token swap.

        Args:
            quote: A TokenQuote previously generated
            slippage_bps: Maximum slippage in basis points (e.g., 100 = 1%)
        """
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
