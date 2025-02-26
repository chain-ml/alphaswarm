from __future__ import annotations

from collections import defaultdict, deque
from decimal import Decimal
from enum import Enum, auto
from typing import Callable, Dict, Iterable, List, Optional, Sequence

from alphaswarm.core.token import TokenInfo

from .portfolio_base import PortfolioSwap


class PnlMode(Enum):
    TOTAL = auto()
    REALIZED = auto()
    UNREALIZED = auto()


class PortfolioPNL:
    def __init__(self) -> None:
        self._details_per_asset: Dict[str, List[PortfolioPNLDetail]] = {}

    def add_details(self, asset: str, details: Iterable[PortfolioPNLDetail]) -> None:
        self._details_per_asset[asset] = list(details)

    def pnl_per_asset(self, mode: PnlMode = PnlMode.TOTAL) -> Dict[str, Decimal]:
        result = {}
        for asset, details in self._details_per_asset.items():
            result[asset] = sum([item.pnl for item in details if item.is_in_scope(mode)], Decimal(0))
        return result

    def pnl(self, mode: PnlMode = PnlMode.TOTAL) -> Decimal:
        return sum([pnl for asset, pnl in self.pnl_per_asset(mode).items()], Decimal(0))

    @classmethod
    def compute_pnl(
        cls, positions: Sequence[PortfolioSwap], base_token: TokenInfo, pricing_function: PricingFunction
    ) -> PortfolioPNL:
        """Compute profit and loss (PNL) for a sequence of portfolio swaps.

        Args:
            positions: Sequence of portfolio swaps to analyze
            base_token: Token to use as the base currency for PNL calculations
            pricing_function: Function that returns current price of an asset in terms of base token (asset_token/base_token)

        Returns:
            PortfolioPNL object containing realized and unrealized PNL details
        """
        items = sorted(positions, key=lambda x: x.block_number)
        per_asset = defaultdict(list)
        for position in items:
            if position.sold.token_info.address == base_token.address:
                per_asset[position.bought.token_info.address].append(position)
            if position.bought.token_info.address == base_token.address:
                per_asset[position.sold.token_info.address].append(position)

        result = PortfolioPNL()
        for asset, swaps in per_asset.items():
            result.add_details(
                asset,
                cls.compute_pnl_fifo_for_pair(swaps, base_token, pricing_function(asset, base_token.address)),
            )

        return result

    @classmethod
    def compute_pnl_fifo_for_pair(
        cls, swaps: List[PortfolioSwap], base_token: TokenInfo, asset_price: Decimal
    ) -> List[PortfolioPNLDetail]:
        purchases: deque[PortfolioSwap] = deque()
        bought_position: Optional[PortfolioSwap] = None
        buy_remaining = Decimal(0)
        result: List[PortfolioPNLDetail] = []
        for swap in swaps:
            if swap.sold.token_info.address == base_token.address:
                purchases.append(swap)
                continue

            sell_remaining = swap.sold.value
            while sell_remaining > 0:
                if buy_remaining <= 0 or bought_position is None:
                    try:
                        bought_position = purchases.popleft()
                    except IndexError:
                        raise RuntimeError("Missing bought position to compute PNL")
                    buy_remaining = bought_position.bought.value

                sold_quantity = min(sell_remaining, buy_remaining)
                result.append(PortfolioRealizedPNLDetail(bought_position, swap, sold_quantity))
                sell_remaining -= sold_quantity
                buy_remaining -= sold_quantity

        if buy_remaining > 0 and bought_position is not None:
            result.append(PortfolioUnrealizedPNLDetail(bought_position, asset_price, buy_remaining))

        for bought_position in purchases:
            result.append(PortfolioUnrealizedPNLDetail(bought_position, asset_price, bought_position.bought.value))

        return result


class PortfolioPNLDetail:
    def __init__(self, bought: PortfolioSwap, selling_price: Decimal, sold_amount: Decimal, is_realized: bool) -> None:
        self._bought = bought
        self._selling_price = selling_price
        self._sold_amount = sold_amount
        self._is_realized = is_realized
        self._pnl = sold_amount * (self._selling_price - self.buying_price)

    @property
    def buying_price(self) -> Decimal:
        """Buying price per asset"""
        return self._bought.sold.value / self._bought.bought.value

    @property
    def sold_amount(self) -> Decimal:
        return self._sold_amount

    @property
    def selling_price(self) -> Decimal:
        return self._selling_price

    @property
    def pnl(self) -> Decimal:
        return self._pnl

    @property
    def is_realized(self) -> bool:
        return self._is_realized

    def is_in_scope(self, mode: PnlMode) -> bool:
        return (
            mode == PnlMode.TOTAL
            or (mode == PnlMode.REALIZED and self._is_realized)
            or (mode == PnlMode.UNREALIZED and not self._is_realized)
        )


class PortfolioRealizedPNLDetail(PortfolioPNLDetail):
    def __init__(self, bought: PortfolioSwap, sold: PortfolioSwap, sold_amount: Decimal) -> None:
        if bought.block_number > sold.block_number:
            raise ValueError("bought block number is greater than sold block number")

        super().__init__(bought, sold.bought.value / sold.sold.value, sold_amount, is_realized=True)
        self._sold = sold


class PortfolioUnrealizedPNLDetail(PortfolioPNLDetail):
    def __init__(self, bought: PortfolioSwap, selling_price: Decimal, sold_amount: Decimal) -> None:
        super().__init__(bought, selling_price, sold_amount, is_realized=False)


PricingFunction = Callable[[str, str], Decimal]
