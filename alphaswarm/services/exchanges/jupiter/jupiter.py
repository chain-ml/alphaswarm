from __future__ import annotations

import logging
from decimal import Decimal
from typing import Annotated, Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import requests
from alphaswarm.config import ChainConfig, Config, JupiterSettings, JupiterVenue, TokenInfo
from alphaswarm.services import ApiException
from alphaswarm.services.exchanges.base import DEXClient, SwapResult, TokenPrice
from pydantic import BaseModel, Field
from pydantic.dataclasses import dataclass

logger = logging.getLogger(__name__)


class SwapInfo(BaseModel):
    amm_key: Annotated[str, Field(alias="ammKey")]
    label: Annotated[Optional[str], Field(alias="label", default=None)]
    input_mint: Annotated[str, Field(alias="inputMint")]
    output_mint: Annotated[str, Field(alias="outputMint")]
    in_amount: Annotated[str, Field(alias="inAmount")]
    out_amount: Annotated[str, Field(alias="outAmount")]
    fee_amount: Annotated[str, Field(alias="feeAmount")]
    fee_mint: Annotated[str, Field(alias="feeMint")]

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(by_alias=True)


@dataclass
class RoutePlan:
    swap_info: Annotated[SwapInfo, Field(alias="swapInfo")]
    percent: int


@dataclass
class QuoteResponse:
    # TODO capture more fields if needed
    out_amount: Annotated[Decimal, Field(alias="outAmount")]
    route_plan: Annotated[List[RoutePlan], Field(alias="routePlan")]

    def route_plan_to_string(self) -> str:
        return "/".join([route.swap_info.amm_key for route in self.route_plan])


class JupiterClient(DEXClient):
    """Client for Jupiter DEX on Solana"""

    def __init__(self, chain_config: ChainConfig, venue_config: JupiterVenue, settings: JupiterSettings) -> None:
        self._validate_chain(chain_config.chain)
        super().__init__(chain_config)
        self._settings = settings
        self._venue_config = venue_config
        logger.info(f"Initialized JupiterClient on chain '{self.chain}'")

    def _validate_chain(self, chain: str) -> None:
        if chain != "solana":
            raise ValueError(f"Chain '{chain}' not supported. JupiterClient only supports Solana chain")

    def swap(
        self,
        quote: TokenPrice,
        slippage_bps: int = 100,
    ) -> SwapResult:
        raise NotImplementedError("Jupiter swap functionality is not yet implemented")

    def get_token_price(self, token_out: TokenInfo, token_in: TokenInfo, amount_in: Decimal) -> TokenPrice:
        # Verify tokens are on Solana
        if not token_out.chain == self.chain or not token_in.chain == self.chain:
            raise ValueError(f"Jupiter only supports Solana tokens. Got {token_out.chain} and {token_in.chain}")

        logger.debug(f"Getting price for {token_out.symbol}/{token_in.symbol} on {token_out.chain} using Jupiter")

        # Prepare query parameters
        params = {
            "inputMint": token_in.address,
            "outputMint": token_out.address,
            "swapMode": "ExactIn",
            "amount": str(token_in.convert_to_wei(Decimal(1))),  # Get price spending exactly 1 token_in
            "slippageBps": self._settings.slippage_bps,
        }

        url = f"{self._venue_config.quote_api_url}?{urlencode(params)}"

        response = requests.get(url)
        if response.status_code != 200:
            raise ApiException(response)

        result = response.json()
        quote = QuoteResponse(**result)

        # Calculate price (token_out per token_in)
        amount_out = quote.out_amount
        price = token_out.convert_from_wei(amount_out)
        # Log quote details
        logger.debug("Quote successful:")
        logger.debug(f"- Input: 1 {token_in.symbol}")
        logger.debug(f"- Output: {amount_out} {token_out.symbol} lamports")
        logger.debug(f"- Price: {price} {token_out.symbol}/{token_in.symbol}")
        logger.debug(f"- Route: {quote.route_plan}")

        return TokenPrice(quote_details=quote)

    def get_markets_for_tokens(self, tokens: List[TokenInfo]) -> List[Tuple[TokenInfo, TokenInfo]]:
        """Get list of valid trading pairs between the provided tokens.

        Args:
            tokens: List of TokenInfo objects to find trading pairs between

        Returns:
            List of tuples containing (base_token, quote_token) for each valid trading pair
        """
        raise NotImplementedError("Not yet implemented for Jupiter")

    @classmethod
    def from_config(cls, config: Config, chain: str) -> JupiterClient:
        chain_config = config.get_chain_config(chain)
        venue_config = config.get_venue_jupiter(chain=chain)
        return cls(chain_config=chain_config, venue_config=venue_config, settings=config.get_venue_settings_jupiter())
