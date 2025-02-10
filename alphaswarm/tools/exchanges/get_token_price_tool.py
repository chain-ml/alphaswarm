import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import List, Optional

from alphaswarm.config import Config
from alphaswarm.services.exchanges import DEXFactory
from pydantic.dataclasses import dataclass
from smolagents import Tool

logger = logging.getLogger(__name__)


@dataclass
class TokenPrice:
    price: Decimal
    source: str


@dataclass
class TokenPriceResult:
    token_out: str
    token_in: str
    timestamp: str
    prices: List[TokenPrice]


class GetTokenPriceTool(Tool):
    name = "get_token_price"
    description = (
        "Get the current price of a token pair from available DEXes. "
        "Returns a list of TokenPriceResult object. "
        "Result is expressed in amount of token_out per token_in. "
        "Examples: 'Get the price of ETH in USDC on ethereum', 'Get the price of GIGA in SOL on solana'"
    )
    inputs = {
        "token_out": {
            "type": "string",
            "description": "The address of the token we want to buy",
        },
        "token_in": {
            "type": "string",
            "description": "The address of the token we want to sell",
        },
        "chain": {
            "type": "string",
            "description": "Blockchain to use. Must be 'solana' for Solana tokens, 'base' for Base tokens, 'ethereum' for Ethereum tokens, 'ethereum_sepolia' for Ethereum Sepolia tokens.",
        },
        "dex_type": {
            "type": "string",
            "description": "Type of DEX to use (e.g. 'uniswap_v2', 'uniswap_v3', 'jupiter'). If not provided, will check all available venues.",
            "nullable": True,
        },
    }
    output_type = "object"

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config

    def forward(
        self,
        token_out: str,
        token_in: str,
        chain: str,
        dex_type: Optional[str] = None,
    ) -> TokenPriceResult:
        """Get token price from DEX(es)"""
        logger.debug(f"Getting price for {token_out}/{token_in} on {chain}")

        # Get prices from all available venues
        venues = self.config.get_trading_venues_for_chain(chain) if dex_type is None else [dex_type]
        prices = []
        for venue in venues:
            try:
                dex = DEXFactory.create(dex_name=venue, config=self.config, chain=chain)

                price = dex.get_token_price(token_out=token_out, token_in=token_in)
                prices.append(TokenPrice(price=price, source=venue))
            except Exception:
                logger.exception(f"Error getting price from {venue}")

        if len(prices) == 0:
            logger.warning(f"No valid prices found for out/in {token_out}/{token_in}")
            raise RuntimeError(f"No valid prices found for {token_out}/{token_in}")

        # Get current timestamp
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

        # If we have multiple prices, return them all
        result = TokenPriceResult(token_out=token_out, token_in=token_in, timestamp=timestamp, prices=prices)
        logger.debug(f"Returning result: {result}")
        return result
