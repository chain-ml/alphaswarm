from __future__ import annotations

from decimal import Decimal
from typing import NewType, Union

from eth_typing import ChecksumAddress
from pydantic import BaseModel
from pydantic.dataclasses import dataclass
from web3 import Web3
from web3.types import Wei

BaseUnit = NewType("BaseUnit", int)


class TokenAmount:

    def __init__(self, token_info: TokenInfo, value: Decimal) -> None:
        self.token_info = token_info
        self.value = value

    @property
    def is_zero(self) -> bool:
        """Check if the token amount is zero"""
        return self.value == Decimal(0)

    def __str__(self) -> str:
        """Return a human-readable string representation like '1.5 ETH'"""
        return f"{self.value:,.8f} {self.token_info.symbol}"

    def __eq__(self, other: object) -> bool:
        """Check if two token amounts are equal (same token and value)"""
        if isinstance(other, TokenAmount):
            return self.token_info == other.token_info and self.base_units == other.base_units
        return False

    def __lt__(self, other: TokenAmount) -> bool:
        """Compare if this amount is less than another (must be same token)"""
        if not isinstance(other, TokenAmount):
            return NotImplemented
        if self.token_info != other.token_info:
            raise ValueError(f"Cannot compare different tokens: {self.token_info.symbol} vs {other.token_info.symbol}")
        return self.base_units < other.base_units

    def __le__(self, other: TokenAmount) -> bool:
        return self < other or self == other

    def __gt__(self, other: TokenAmount) -> bool:
        return not (self <= other)

    def __ge__(self, other: TokenAmount) -> bool:
        return not (self < other)

    @property
    def base_units(self) -> BaseUnit:
        """Get the token amount in base units (e.g. wei for ETH, atomic for SOL)"""
        return self.token_info.convert_to_base_units(self.value)


class TokenInfo(BaseModel):
    symbol: str
    address: str
    decimals: int
    chain: str
    is_native: bool = False

    def convert_to_base_units(self, amount: Decimal) -> BaseUnit:
        return BaseUnit(int(amount * (10**self.decimals)))

    def convert_from_base_units(self, amount: Union[BaseUnit, Wei]) -> Decimal:
        return Decimal(amount) / (10**self.decimals)

    def to_amount(self, value: Decimal) -> TokenAmount:
        """Create a TokenAmount with a decimal value"""
        return TokenAmount(self, value)

    def to_zero_amount(self) -> TokenAmount:
        """Create a TokenAmount with a zero value"""
        return TokenAmount(self, Decimal("0"))

    def to_amount_from_base_units(self, base_value: Union[BaseUnit, Wei]) -> TokenAmount:
        """Create a TokenAmount from base units value (e.g. wei for ETH, atomic for SOL)"""

        return TokenAmount(self, self.convert_from_base_units(base_value))

    def address_to_path(self) -> str:
        # Remove '0x' and pad to 20 bytes
        return self.address.removeprefix("0x").zfill(40)

    @property
    def checksum_address(self) -> ChecksumAddress:
        """Get the checksum address for this token"""
        return Web3.to_checksum_address(self.address)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, TokenInfo):
            return self.address == other.address and self.chain == other.chain
        return False

    @classmethod
    def Ethereum(cls) -> TokenInfo:
        return cls(symbol="ETH", decimals=18, is_native=True, chain="ethereum", address="")
