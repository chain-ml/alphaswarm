from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import List

from alphaswarm.config import WalletInfo
from alphaswarm.core.token import TokenAmount


@dataclass
class PortfolioSwap:
    sold: TokenAmount
    bought: TokenAmount
    hash: str
    block_number: int

    def to_short_string(self) -> str:
        return f"{self.sold} -> {self.bought} ({self.sold.token_info.chain} {self.block_number} {self.hash})"


class PortfolioBase:
    def __init__(self, wallet: WalletInfo) -> None:
        self._wallet = wallet

    @abstractmethod
    def get_token_balances(self) -> List[TokenAmount]:
        pass

    @abstractmethod
    def get_swaps(self) -> List[PortfolioSwap]:
        pass

    @property
    def chain(self) -> str:
        return self._wallet.chain
