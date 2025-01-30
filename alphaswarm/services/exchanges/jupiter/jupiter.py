import logging
from decimal import Decimal
from typing import Any, Dict, List, Tuple
from urllib.parse import urlencode

import requests
from alphaswarm.config import Config, TokenInfo
from alphaswarm.services import ApiException
from alphaswarm.services.exchanges.base import DEXClient, SwapResult
from pydantic import Field
from pydantic.dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class QuoteResponse:
    # TODO capture more fields if needed
    out_amount: Decimal = Field(alias="outAmount")
    route_plan: List[Dict[str, Any]] = Field(alias="routePlan")


class JupiterClient(DEXClient):
    """Client for Jupiter DEX on Solana"""

    def __init__(self, config: Config, chain: str) -> None:
        if chain != "solana":
            raise ValueError("JupiterClient only supports Solana chain")
        super().__init__(config, chain)
        logger.info("Initialized JupiterClient")

    def swap(
        self,
        base_token: TokenInfo,
        quote_token: TokenInfo,
        quote_amount: float,
        slippage_bps: int = 100,
    ) -> SwapResult:
        """Execute a token swap on Jupiter (Not Implemented)"""
        raise NotImplementedError("Jupiter swap functionality is not yet implemented")

    def get_token_price(self, base_token: TokenInfo, quote_token: TokenInfo) -> Decimal:
        """Get token price.

        Gets the current price from Jupiter based on the client version.
        The price is returned in terms of base/quote (how much quote token per base token).

        Args:
            base_token (TokenInfo): Base token info (token being priced)
            quote_token (TokenInfo): Quote token info (denominator token)

        Returns:
            Decimal: Current price in base/quote terms
        """
        # Verify tokens are on Solana
        if not base_token.chain == "solana" or not quote_token.chain == "solana":
            raise ValueError(f"Jupiter only supports Solana tokens. Got {base_token.chain} and {quote_token.chain}")

        logger.debug(f"Getting price for {base_token.symbol}/{quote_token.symbol} on {base_token.chain} using Jupiter")

        # Prepare query parameters
        params = {
            "inputMint": base_token.address,
            "outputMint": quote_token.address,
            "amount": str(base_token.convert_to_wei(Decimal(1))),  # Get price for 1 full token
            "slippageBps": self.config.get_venue_settings_jupiter().slippage_bps,
        }

        venue_config = self.config.get_venue_jupiter("solana")
        url = f"{venue_config.quote_api_url}?{urlencode(params)}"

        response = requests.get(url)
        if response.status_code != 200:
            raise ApiException(response)

        result = response.json()
        quote = QuoteResponse(**result)

        # Calculate price (quote_token per base_token)
        amount_out = quote.out_amount
        price = quote_token.convert_from_wei(amount_out)
        # Log quote details
        logger.debug("Quote successful:")
        logger.debug(f"- Input: 1 {base_token.symbol}")
        logger.debug(f"- Output: {amount_out} {quote_token.symbol} lamports")
        logger.debug(f"- Price: {price} {quote_token.symbol}/{base_token.symbol}")
        logger.debug(f"- Route: {quote.route_plan}")

        return price

    def get_markets_for_tokens(self, tokens: List[TokenInfo]) -> List[Tuple[TokenInfo, TokenInfo]]:
        """Get list of valid trading pairs between the provided tokens.

        Args:
            tokens: List of TokenInfo objects to find trading pairs between

        Returns:
            List of tuples containing (base_token, quote_token) for each valid trading pair
        """
        raise NotImplementedError("Not yet implemented for Jupiter")
