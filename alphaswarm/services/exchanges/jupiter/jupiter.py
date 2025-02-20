from __future__ import annotations

import base64
import logging
from typing import Annotated, Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import requests
from alphaswarm.config import ChainConfig, Config, JupiterSettings, JupiterVenue, TokenInfo
from alphaswarm.core.token import BaseUnit, TokenAmount
from alphaswarm.services import ApiException
from alphaswarm.services.chains.solana import SolanaClient, SolSigner
from alphaswarm.services.exchanges.base import DEXClient, QuoteResult, SwapResult
from pydantic import BaseModel, Field
from pydantic.dataclasses import dataclass
from solders.transaction import VersionedTransaction

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
class JupiterQuote:
    quote: Dict[str, Any]

    @property
    def out_amount(self) -> BaseUnit:
        return BaseUnit(self.quote["outAmount"])


class JupiterSwapTransaction:
    def __init__(self, swap_transaction: Dict[str, Any]):
        self._swap_transaction = swap_transaction

    @property
    def swap_transaction_base64(self) -> str:
        return self._swap_transaction["swapTransaction"]

    def decode_transaction(self) -> VersionedTransaction:
        tx_bytes = base64.b64decode(self.swap_transaction_base64)
        return VersionedTransaction.from_bytes(tx_bytes)


class JupiterClient(DEXClient[JupiterQuote]):
    """Client for Jupiter DEX on Solana"""

    def __init__(self, chain_config: ChainConfig, venue_config: JupiterVenue, settings: JupiterSettings) -> None:
        self._validate_chain(chain_config.chain)
        super().__init__(chain_config, JupiterQuote)
        self._settings = settings
        self._venue_config = venue_config
        self._client = SolanaClient(chain_config)
        logger.info(f"Initialized JupiterClient on chain '{self.chain}'")

    def _validate_chain(self, chain: str) -> None:
        if chain != "solana":
            raise ValueError(f"Chain '{chain}' not supported. JupiterClient only supports Solana chain")

    @property
    def wallet_address(self) -> str:
        return self._chain_config.wallet_address

    @property
    def signer(self) -> SolSigner:
        return SolSigner(self._chain_config.private_key)

    def swap(
        self,
        quote: QuoteResult[JupiterQuote],
        slippage_bps: int = 100,
    ) -> SwapResult:
        tx = self._build_swap_transaction(quote.quote)
        tx_signature = self._client.process(tx.decode_transaction(), self.signer)
        return SwapResult.build_success(quote.amount_out, quote.amount_in, str(tx_signature))

    def get_token_price(self, token_out: TokenInfo, amount_in: TokenAmount) -> QuoteResult[JupiterQuote]:
        # Verify tokens are on Solana
        token_in = amount_in.token_info
        if not token_out.chain == self.chain or not token_in.chain == self.chain:
            raise ValueError(f"Jupiter only supports Solana tokens. Got {token_out.chain} and {token_in.chain}")

        logger.debug(f"Getting amount_out for {token_out.symbol}/{token_in.symbol} on {token_out.chain} using Jupiter")

        # Prepare query parameters
        quote = self._get_quote(token_out, amount_in)

        # Calculate amount_out (token_out per token_in)
        raw_out = BaseUnit(quote.out_amount)
        amount_out = token_out.to_amount_from_base_units(raw_out)
        # Log quote details
        logger.debug("Quote successful:")
        logger.debug(f"- Input: {amount_in}")
        logger.debug(f"- Output: {amount_out}")
        logger.debug(f"- Ratio: {amount_out.value/amount_in.value} {token_out.symbol}/{token_in.symbol}")

        return QuoteResult(
            quote=quote,
            token_in=token_in,
            token_out=token_out,
            amount_in=amount_in.value,
            amount_out=amount_out.value,
        )

    def _get_quote(self, token_out: TokenInfo, amount_in: TokenAmount) -> JupiterQuote:
        params = {
            "inputMint": amount_in.token_info.address,
            "outputMint": token_out.address,
            "swapMode": "ExactIn",
            "amount": str(amount_in.base_units),
            "slippageBps": self._settings.slippage_bps,
            "restrictIntermediateTokens": "true",
        }

        url = f"{self._venue_config.quote_api_url}?{urlencode(params)}"
        response = requests.get(url)
        if response.status_code != 200:
            raise ApiException(response)
        quote = JupiterQuote(quote=response.json())
        return quote

    def _build_swap_transaction(self, quote: JupiterQuote) -> JupiterSwapTransaction:
        params = {
            "quoteResponse": quote.quote,
            "userPublicKey": self.wallet_address,
            "dynamicComputeUnitLimit": True,
        }
        headers = {
            "Content-Type": "application/json",
        }
        response = requests.post(self._venue_config.swap_api_url, json=params, headers=headers)
        if response.status_code != 200:
            raise ApiException(response)
        logger.debug(response.json())
        return JupiterSwapTransaction(response.json())

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
