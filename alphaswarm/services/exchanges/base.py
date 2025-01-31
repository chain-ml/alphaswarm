from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional, Tuple

from alphaswarm.config import Config, TokenInfo
from hexbytes import HexBytes


@dataclass
class SwapResult:
    success: bool
    base_amount: Decimal
    quote_amount: Decimal
    tx_hash: Optional[str] = None
    error: Optional[str] = None

    @classmethod
    def build_error(cls, error: str, base_amount: Decimal) -> SwapResult:
        return cls(success=False, base_amount=base_amount, quote_amount=Decimal(0), error=error)

    @classmethod
    def build_success(cls, base_amount: Decimal, quote_amount: Decimal, tx_hash: HexBytes) -> SwapResult:
        return cls(success=True, base_amount=base_amount, quote_amount=quote_amount, tx_hash=tx_hash.hex())


class DEXClient(ABC):
    """Base class for DEX clients"""

    @abstractmethod
    def __init__(self, config: Config, chain: str) -> None:
        """Initialize the DEX client with configuration"""
        self._config = config
        self._chain = chain

    @property
    def config(self) -> Config:
        return self._config

    @property
    def chain(self) -> str:
        return self._chain

    @abstractmethod
    def get_token_price(self, base_token: TokenInfo, quote_token: TokenInfo) -> Decimal:
        """Get current token price.

        Gets the current price from either Uniswap V2 or V3 pools based on the client version.
        The price is returned in terms of base/quote (how much quote token per base token).

        Args:
            base_token (TokenInfo): Base token info (token being priced)
            quote_token (TokenInfo): Quote token info (denominator token)

        Example:
            eth_token = TokenInfo(address="0x...", decimals=18, symbol="ETH", chain="ethereum")
            usdc_token = TokenInfo(address="0x...", decimals=6, symbol="USDC", chain="ethereum")
            get_token_price(eth_token, usdc_token)
            Returns: The price of 1 ETH in USDC
        """
        pass

    # TODO: using `float` for the amount is potentially dangerous because of precision limitation and rounding issues.
    @abstractmethod
    def swap(
        self,
        base_token: TokenInfo,
        quote_token: TokenInfo,
        quote_amount: Decimal,
        slippage_bps: int = 100,
    ) -> SwapResult:
        """Execute a token swap on the DEX

        Args:
            base_token: TokenInfo object for the token being sold
            quote_token: TokenInfo object for the token being bought
            quote_amount: Amount of quote_token to spend (output amount)
            slippage_bps: Maximum allowed slippage in basis points (1 bp = 0.01%)

        Returns:
            SwapResult: Result object containing success status, transaction hash and any error details

        Example:
            eth = TokenInfo(address="0x...", decimals=18, symbol="ETH", chain="ethereum")
            usdc = TokenInfo(address="0x...", decimals=6, symbol="USDC", chain="ethereum")
            result = swap(eth, usdc, 1000.0, "0xprivatekey...", slippage_bps=100)
            # Swaps ETH for 1000 USDC with 1% max slippage
        """
        pass

    @abstractmethod
    def get_markets_for_tokens(self, tokens: List[TokenInfo]) -> List[Tuple[TokenInfo, TokenInfo]]:
        """Get list of valid trading pairs between the provided tokens.

        Args:
            tokens: List of TokenInfo objects to find trading pairs between

        Returns:
            List of tuples containing (base_token, quote_token) for each valid trading pair
        """
        pass
