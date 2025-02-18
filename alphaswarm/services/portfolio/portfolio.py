from __future__ import annotations

from typing import Sequence
from ...config import WalletInfo



class Portfolio:
    def __init__(self, wallets: Sequence[WalletInfo]) -> None:
        self._wallets = wallets
