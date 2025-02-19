from __future__ import annotations

from decimal import Decimal
from typing import Union

from eth_typing import ChecksumAddress
from pydantic.dataclasses import dataclass
from web3 import Web3


@dataclass
class TokenInfo:
    symbol: str
    address: str
    decimals: int
    chain: str
    is_native: bool = False

    def convert_to_wei(self, amount: Decimal) -> int:
        return int(amount * (10**self.decimals))

    def convert_from_wei(self, amount: Union[int, Decimal]) -> Decimal:
        return Decimal(amount) / (10**self.decimals)

    def address_to_path(self) -> str:
        # Remove '0x' and pad to 20 bytes
        return self.address.removeprefix("0x").zfill(40)

    @property
    def checksum_address(self) -> ChecksumAddress:
        """Get the checksum address for this token"""
        return Web3.to_checksum_address(self.address)


@dataclass
class TokenAmount:
    token_info: TokenInfo
    value: Decimal
