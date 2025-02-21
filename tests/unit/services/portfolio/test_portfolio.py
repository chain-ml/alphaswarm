from decimal import Decimal
from typing import List, Tuple, Union

import pytest

from alphaswarm.core.token import TokenAmount, TokenInfo
from alphaswarm.services.portfolio.portfolio import PortfolioBase, PortfolioPNLDetail, PortfolioSwap


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


def assert_pnl_detail(
    item: PortfolioPNLDetail,
    *,
    sold_amount: Union[int, str],
    buying_price: Union[int, str],
    selling_price: Union[int, str],
    pnl: Union[int, str],
) -> None:
    assert item.sold_amount == Decimal(sold_amount)
    assert item.buying_price == Decimal(buying_price)
    assert item.selling_price == Decimal(selling_price)
    assert item.pnl == Decimal(pnl)


def test_portfolio_compute_pnl_fifo_one_asset__sell_from_first_swap(weth: TokenInfo, usdc: TokenInfo) -> None:
    positions = create_swaps(
        [
            (1, weth, 10, usdc),
            (5, usdc, 2, weth),
            (1, weth, 8, usdc),
            (2, usdc, 2, weth),
        ]
    )

    pnl = PortfolioBase.compute_pnl_fifo(positions, weth)
    usdc_pnl = pnl._details_per_asset[usdc.address]
    assert_pnl_detail(usdc_pnl[0], sold_amount=5, buying_price="0.1", selling_price="0.4", pnl="1.5")
    assert_pnl_detail(usdc_pnl[1], sold_amount=2, buying_price="0.1", selling_price="1", pnl="1.8")
    assert pnl.pnl() == Decimal("3.3")


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

    pnl = PortfolioBase.compute_pnl_fifo(positions, weth)
    usdc_pnl = pnl._details_per_asset[usdc.address]
    assert_pnl_detail(usdc_pnl[0], sold_amount=5, buying_price="0.1", selling_price=".15", pnl=".25")
    assert_pnl_detail(usdc_pnl[1], sold_amount=5, buying_price="0.1", selling_price="1", pnl="4.5")
    assert_pnl_detail(usdc_pnl[2], sold_amount=2, buying_price="0.2", selling_price="1", pnl="1.6")
    assert_pnl_detail(usdc_pnl[3], sold_amount=3, buying_price="0.2", selling_price="0.01", pnl="-0.57")
    assert pnl.pnl() == Decimal("5.78")
