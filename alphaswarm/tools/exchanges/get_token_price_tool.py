import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import List, Optional, Union

from alphaswarm.config import Config
from alphaswarm.services.exchanges import DEXFactory, QuoteResult
from alphaswarm.services.exchanges.jupiter.jupiter import JupiterQuote
from alphaswarm.services.exchanges.uniswap.uniswap_client_base import UniswapQuote
from pydantic.dataclasses import dataclass
from smolagents import Tool

logger = logging.getLogger(__name__)


@dataclass
class TokenQuote:
    datetime: str
    dex: str
    chain: str
    quote: QuoteResult[Union[UniswapQuote, JupiterQuote]]


@dataclass
class TokenPriceResult:
    quotes: List[TokenQuote]


class GetTokenPriceTool(Tool):
    name = "get_token_price"
    description = (
        "Get the current price of a token pair from available DEXes. "
        f"Returns a {TokenPriceResult.__name__} object containing a list of {TokenQuote.__name__} objects."
        "Examples: 'Get the price of 1 ETH in USDC on ethereum', 'Get the price of 1 GIGA in SOL on solana'"
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
        "amount_in": {"type": "string", "description": "The amount token_in to be sold, in Token", "required": True},
        "chain": {
            "type": "string",
            "description": "Blockchain to use. Must be 'solana' for Solana tokens, 'base' for Base tokens, "
            "'ethereum' for Ethereum tokens, 'ethereum_sepolia' for Ethereum Sepolia tokens.",
            "enum": ["solana", "base", "ethereum", "ethereum_sepolia"],
        },
        "dex_type": {
            "type": "string",
            "description": "Type of DEX to use. If not provided, will check all available venues.",
            "enum": ["uniswap_v2", "uniswap_v3", "jupiter"],
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
        amount_in: str,
        chain: str,
        dex_type: Optional[str] = None,
    ) -> TokenPriceResult:
        """Get token price from DEX(es)"""
        logger.debug(f"Getting price for {token_out}/{token_in} on {chain}")

        # Get token info and create TokenInfo objects
        chain_config = self.config.get_chain_config(chain)
        token_out_info = chain_config.get_token_info_by_address(token_out)
        token_in_info = chain_config.get_token_info_by_address(token_in)

        logger.debug(f"Token info - Out: {token_out}, In: {token_in}")

        # Get prices from all available venues
        venues = self.config.get_trading_venues_for_chain(chain) if dex_type is None else [dex_type]
        prices: List[TokenQuote] = []
        for venue in venues:
            try:
                dex = DEXFactory.create(dex_name=venue, config=self.config, chain=chain)

                price = dex.get_token_price(token_out_info, token_in_info, amount_in=Decimal(amount_in))
                timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

                prices.append(TokenQuote(dex=venue, chain=chain, quote=price, datetime=timestamp))
            except Exception:
                logger.exception(f"Error getting price from {venue}")

        if len(prices) == 0:
            logger.warning(f"No valid prices found for out/in {token_out}/{token_in}")
            raise RuntimeError(f"No valid prices found for {token_out}/{token_in}")

        # Get current timestamp

        # If we have multiple prices, return them all
        result = TokenPriceResult(quotes=prices)
        logger.debug(f"Returning result: {result}")
        return result
