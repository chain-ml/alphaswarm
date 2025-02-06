import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import List, Optional, Sequence

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
    base_token: str
    quote_token: str
    timestamp: str
    prices: List[TokenPrice]


class GetTokenPriceTool(Tool):
    name = "get_token_price"
    description = "Get the current price of a token pair from available DEXes. For Solana tokens like GIGA/SOL, make sure to set chain='solana'. For Base tokens, set chain='base'. Examples: 'Get the price of ETH in USDC on ethereum', 'Get the price of GIGA in SOL on solana'"
    inputs = {
        "base_token": {
            "type": "string",
            "description": "Base token symbol (e.g., 'ETH', 'GIGA'). The token we want to buy.",
        },
        "quote_token": {
            "type": "string",
            "description": "Quote token symbol (e.g., 'USDC', 'SOL'). The token we want to sell.",
        },
        "dex_type": {
            "type": "string",
            "description": "Type of DEX to use (e.g. 'uniswap_v2', 'uniswap_v3', 'jupiter'). If not provided, will check all available venues.",
            "nullable": True,
        },
        "chain": {
            "type": "string",
            "description": "Blockchain to use. Must be 'solana' for Solana tokens, 'base' for Base tokens, 'ethereum' for Ethereum tokens, 'ethereum_sepolia' for Ethereum Sepolia tokens.",
            "default": "ethereum",
            "nullable": True,
        },
    }
    output_type = "object"

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config

    def _find_venues_for_pair(
        self, base_token: str, quote_token: str, chain: str, specific_venue: Optional[str] = None
    ) -> Sequence[str]:
        """Find all venues that support a given token pair on a chain"""
        return self.config.get_trading_venues_for_token_pair(base_token, quote_token, chain, specific_venue)

    def forward(
        self, base_token: str, quote_token: str, dex_type: Optional[str] = None, chain: str = "ethereum"
    ) -> TokenPriceResult:
        """Get token price from DEX(es)"""
        # TODO: Debug "ERROR - Error getting price: Event loop is closed" when invoked.
        logger.debug(f"Getting price for {base_token}/{quote_token} on {chain}")

        # Find available venues for this pair
        venues = self._find_venues_for_pair(base_token, quote_token, chain, dex_type)
        if len(venues) == 0:
            logger.warning(f"No venues found for pair {base_token}_{quote_token} on {chain}")
            raise RuntimeError(f"No venues found for pair {base_token}_{quote_token} on {chain}")

        # Get token info and create TokenInfo objects
        chain_config = self.config.get_chain_config(chain)
        base_token_info = chain_config.tokens[base_token]
        quote_token_info = chain_config.tokens[quote_token]

        logger.debug(f"Token info - Base: {base_token}, Quote: {quote_token}")

        # Get prices from all available venues
        prices = []
        for venue in venues:
            try:
                dex = DEXFactory.create(dex_name=venue, config=self.config, chain=chain)
                price = dex.get_token_price(base_token_info, quote_token_info)
                prices.append(TokenPrice(price=price, source=venue))
            except Exception:
                logger.exception(f"Error getting price from {venue}")

        if len(prices) == 0:
            logger.warning(f"No valid prices found for {base_token}/{quote_token}")
            raise RuntimeError(f"No valid prices found for {base_token}/{quote_token}")

        # Get current timestamp
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

        # If we have multiple prices, return them all
        result = TokenPriceResult(base_token=base_token, quote_token=quote_token, timestamp=timestamp, prices=prices)
        logger.debug(f"Returning result: {result}")
        return result
