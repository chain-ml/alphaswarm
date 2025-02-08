from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional, Tuple, Type, TypeVar, Union

from alphaswarm.config import ChainConfig, Config, TokenInfo
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


@dataclass
class Slippage:
    """
    Represents slippage tolerance for trades
    Attributes:
        bps (int): Basis points (1 bps = 0.01%)
    """

    base_point: int = 10000

    def __init__(self, bps: int = 100) -> None:
        if not 0 <= bps <= self.base_point:
            raise ValueError("Slippage must be between 0 and 10000 basis points (0% to 100%)")
        self.bps = bps

    @classmethod
    def from_percentage(cls, percentage: Union[float, Decimal]) -> Slippage:
        """Create Slippage from percentage value (e.g., 100.0 for 1%)"""
        bps = int(float(percentage) * 100)
        return cls(bps=bps)

    def to_percentage(self) -> float:
        """Convert basis points to percentage"""
        return self.bps / 100.0

    def to_multiplier(self) -> Decimal:
        """Convert to multiplier for price calculations (e.g., 0.99 for 1% slippage)"""
        return Decimal(1) - (Decimal(self.bps) / Decimal(self.base_point))

    def calculate_minimum_amount(self, amount: Union[int, str, Decimal]) -> int:
        """Calculate minimum amount after slippage"""
        return int(Decimal(amount) * self.to_multiplier())

    def __str__(self) -> str:
        return f"{self.bps} bps"

    def __repr__(self) -> str:
        return f"Slippage(bps={self.bps})"


T = TypeVar("T", bound="DEXClient")


class DEXClient(ABC):
    """Base class for DEX clients"""

    @abstractmethod
    def __init__(self, chain_config: ChainConfig) -> None:
        """Initialize the DEX client with configuration"""
        self._chain_config = chain_config

    @property
    def chain(self) -> str:
        return self._chain_config.chain

    @property
    def chain_config(self) -> ChainConfig:
        return self._chain_config

    @abstractmethod
    def get_token_price(self, token_out: TokenInfo, token_in: TokenInfo) -> Decimal:
        """Get price/conversion rate for the pair of tokens.

        The price is returned in terms of token_out/token_in (how much token out per token in).

        Args:
            token_out (TokenInfo): The token to be bought (going out from the pool)
            token_in (TokenInfo): The token to be sold (going into the pool)

        Example:
            eth_token = TokenInfo(address="0x...", decimals=18, symbol="ETH", chain="ethereum")
            usdc_token = TokenInfo(address="0x...", decimals=6, symbol="USDC", chain="ethereum")
            get_token_price(eth_token, usdc_token)
            Returns: The amount of ETH for 1 USDC
        """
        pass

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

    @classmethod
    @abstractmethod
    def from_config(cls: Type[T], config: Config, chain: str) -> T:
        """Create a DEX client instance from configuration

        Args:
            config: Chain-specific configuration
            chain: Chain name (e.g., "ethereum", "base")

        Returns:
            An instance of the DEX client
        """
        pass
