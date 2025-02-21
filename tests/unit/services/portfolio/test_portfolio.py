from decimal import Decimal
from typing import List, Tuple, Union

import pytest

from alphaswarm.core.token import TokenAmount, TokenInfo
from alphaswarm.services.portfolio.portfolio import (
    PnlMode,
    PortfolioBase,
    PortfolioPNLDetail,
    PortfolioSwap,
)


def create_swaps(
    swaps: List[Tuple[Union[int, str, Decimal], TokenInfo, Union[int, str, Decimal], TokenInfo]]
) -> List[PortfolioSwap]:
    result = []
    block_number = 0
    for amount_sold, asset_sold, amount_bought, asset_bought in swaps:
        result.append(
            PortfolioSwap(
                sold=TokenAmount(value=Decimal(amount_sold), token_info=asset_sold),
                bought=TokenAmount(value=Decimal(amount_bought), token_info=asset_bought),
                block_number=block_number,
                hash=str(block_number),
            )
        )
        block_number += 1
    return result


@pytest.fixture
def usdc() -> TokenInfo:
    return TokenInfo(symbol="USDC", address="0xUSDC", decimals=6, chain="chain")


@pytest.fixture
def weth() -> TokenInfo:
    return TokenInfo(symbol="WETH", address="0xWETH", decimals=18, chain="chain")


def assert_detail(
    item: PortfolioPNLDetail,
    *,
    sold_amount: Union[int, str],
    buying_price: Union[int, str],
    selling_price: Union[int, str],
    pnl: Union[int, str],
    realized: bool,
) -> None:
    assert item.sold_amount == Decimal(sold_amount)
    assert item.buying_price == Decimal(buying_price)
    assert item.selling_price == Decimal(selling_price)
    assert item.pnl == Decimal(pnl)
    assert item.is_realized == realized


def test_portfolio_compute_pnl_fifo_one_asset__sell_from_first_swap(weth: TokenInfo, usdc: TokenInfo) -> None:
    positions = create_swaps(
        [
            (1, weth, 10, usdc),
            (5, usdc, 2, weth),
            (1, weth, 8, usdc),
            (2, usdc, 2, weth),
        ]
    )

    pnl = PortfolioBase.compute_pnl(positions, weth, lambda asset, base: Decimal(1))

    usdc_pnl = iter(pnl._details_per_asset[usdc.address])
    assert_detail(next(usdc_pnl), sold_amount=5, buying_price="0.1", selling_price="0.4", pnl="1.5", realized=True)
    assert_detail(next(usdc_pnl), sold_amount=2, buying_price="0.1", selling_price="1", pnl="1.8", realized=True)
    assert_detail(next(usdc_pnl), sold_amount=3, buying_price="0.1", selling_price="1", pnl="2.7", realized=False)
    assert_detail(next(usdc_pnl), sold_amount=8, buying_price="0.125", selling_price="1", pnl="7", realized=False)
    assert next(usdc_pnl, None) is None
    assert pnl.pnl(PnlMode.REALIZED) == Decimal("3.3")
    assert pnl.pnl(PnlMode.UNREALIZED) == Decimal("9.7")
    assert pnl.pnl() == Decimal("13")


def test_portfolio_compute_pnl_fifo_one_asset__sell_from_multiple_swaps(weth: TokenInfo, usdc: TokenInfo) -> None:
    positions = create_swaps(
        [
            (1, weth, 10, usdc),
            (1, weth, 5, usdc),
            (5, usdc, ".75", weth),
            (7, usdc, "7", weth),
            (3, usdc, "0.03", weth),
        ]
    )

    pnl = PortfolioBase.compute_pnl(positions, weth, lambda asset, base: Decimal(1))
    usdc_pnl = iter(pnl._details_per_asset[usdc.address])
    assert_detail(next(usdc_pnl), sold_amount=5, buying_price="0.1", selling_price=".15", pnl=".25", realized=True)
    assert_detail(next(usdc_pnl), sold_amount=5, buying_price="0.1", selling_price="1", pnl="4.5", realized=True)
    assert_detail(next(usdc_pnl), sold_amount=2, buying_price="0.2", selling_price="1", pnl="1.6", realized=True)
    assert_detail(next(usdc_pnl), sold_amount=3, buying_price="0.2", selling_price="0.01", pnl="-0.57", realized=True)
    assert next(usdc_pnl, None) is None
    assert pnl.pnl(PnlMode.REALIZED) == Decimal("5.78")
    assert pnl.pnl(PnlMode.UNREALIZED) == Decimal(0)
    assert pnl.pnl() == Decimal("5.78")


def test_portoflio_compute_pnl__bought_exhausted_raise_exception(weth: TokenInfo, usdc: TokenInfo) -> None:
    positions = create_swaps(
        [
            (1, weth, 10, usdc),
            (9, usdc, 1, weth),
            (2, usdc, 1, weth),
        ]
    )

    with pytest.raises(RuntimeError):
        PortfolioBase.compute_pnl(positions, weth, lambda asset, base: Decimal(1))
