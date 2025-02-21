from decimal import Decimal
from typing import List, Tuple, Union

import pytest

from alphaswarm.core.token import TokenAmount, TokenInfo
from alphaswarm.services.portfolio.portfolio import PortfolioBase, PortfolioSwap


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


def test_portfolio_compute_pnl_fifo_one_asset(weth: TokenInfo, usdc: TokenInfo) -> None:
    positions = create_swaps(
        [
            (1, weth, 10, usdc),
            (5, usdc, "0.6", weth),
            (1, weth, 8, usdc),
            (7, usdc, ".65", weth),
            (6, usdc, "0.75", weth),
        ]
    )

    pnl = PortfolioBase.compute_pnl_fifo(positions, weth)
    assert pnl.pnl() == Decimal(0)
