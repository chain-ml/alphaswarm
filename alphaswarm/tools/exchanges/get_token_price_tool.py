import logging
from datetime import UTC, datetime
from typing import Dict, Optional, Sequence

from alphaswarm.config import Config
from alphaswarm.services.exchanges import DEXFactory
from smolagents import Tool

logger = logging.getLogger(__name__)


class GetTokenPriceTool(Tool):
    name = "get_token_price"
    description = "Get the current price of a token pair from available DEXes. For Solana tokens like GIGA/SOL, make sure to set chain='solana'. For Base tokens, set chain='base'. Examples: 'Get the price of ETH in USDC on ethereum', 'Get the price of GIGA in SOL on solana'"
    inputs = {
        "base_token": {
            "type": "string",
            "description": "Base token symbol (e.g., 'ETH', 'GIGA'). The token we want to buy.",
            "required": True,
        },
        "quote_token": {
            "type": "string",
            "description": "Quote token symbol (e.g., 'USDC', 'SOL'). The token we want to sell.",
            "required": True,
        },
        "dex_type": {
            "type": "string",
            "description": "Type of DEX to use (e.g. 'uniswap_v2', 'uniswap_v3', 'jupiter'). If not provided, will check all available venues.",
            "required": False,
            "default": None,
            "nullable": True,
        },
        "chain": {
            "type": "string",
            "description": "Blockchain to use. Must be 'solana' for Solana tokens, 'base' for Base tokens, 'ethereum' for Ethereum tokens, 'ethereum_sepolia' for Ethereum Sepolia tokens.",
            "required": False,
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
    ) -> Optional[Dict]:
        """Get token price from DEX(es)"""
        # TODO: Debug "ERROR - Error getting price: Event loop is closed" when invoked.
        try:
            logger.debug(f"Getting price for {base_token}/{quote_token} on {chain}")

            # Find available venues for this pair
            venues = self._find_venues_for_pair(base_token, quote_token, chain, dex_type)
            if not venues:
                logger.warning(f"No venues found for pair {base_token}_{quote_token} on {chain}")
                return {
                    "error": f"Pair {base_token}_{quote_token} not supported on {chain}",
                    "base_token": base_token,
                    "quote_token": quote_token,
                    "chain": chain,
                }

            # Get token info and create TokenInfo objects
            try:
                chain_config = self.config.get_chain_config(chain)
                base_token_info = chain_config.tokens[base_token]
                quote_token_info = chain_config.tokens[quote_token]

            except KeyError:
                logger.warning(f"Token info not found for {base_token} or {quote_token} on {chain}")
                return {
                    "error": f"Token info not found for {base_token} or {quote_token} on {chain}",
                    "base_token": base_token,
                    "quote_token": quote_token,
                    "chain": chain,
                }

            logger.debug(f"Token info - Base: {base_token}, Quote: {quote_token}")

            # Get prices from all available venues
            prices = []
            for venue in venues:
                try:
                    dex = DEXFactory.create(venue, self.config, chain)
                    price = dex.get_token_price(base_token_info, quote_token_info)

                    if price is not None:
                        prices.append({"price": price, "source": venue})
                except Exception as e:
                    logger.error(f"Error getting price from {venue}: {str(e)}")

            if not prices:
                logger.warning(f"No valid prices found for {base_token}/{quote_token}")
                return None

            # Get current timestamp
            timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

            # If we have multiple prices, return them all
            result = {"base_token": base_token, "quote_token": quote_token, "timestamp": timestamp, "prices": prices}
            logger.debug(f"Returning result: {result}")
            return result

        except Exception as e:
            logger.error(f"Error getting price: {str(e)}")
            return None
