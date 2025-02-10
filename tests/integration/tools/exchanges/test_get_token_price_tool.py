from typing import Optional

import pytest

from alphaswarm.tools.exchanges import GetTokenPriceTool
from alphaswarm.config import Config


@pytest.mark.parametrize(
    "dex,chain,token_out,token_in,ratio",
    [
        ("jupiter", "solana", "GIGA", "SOL", 1000),
        ("uniswap_v3", "base", "VIRTUAL", "WETH", 1000),
        ("uniswap_v3", "ethereum_sepolia", "USDC", "WETH", 100),
        ("uniswap_v3", "ethereum", "USDC", "WETH", 100),
        ("uniswap_v2", "ethereum", "USDC", "WETH", 100),
        (None, "ethereum", "USDC", "WETH", 100),
    ],
)
def test_get_token_price_tool(
    dex: Optional[str], chain: str, token_out: str, token_in: str, ratio: int, default_config: Config
) -> None:
    config = default_config
    tool = GetTokenPriceTool(config)
    result = tool.forward(token_out=token_out, token_in=token_in, dex_type=dex, chain=chain)

    assert len(result.prices) > 0, "at least one price is expected"
    item = result.prices[0]
    assert item.price > ratio, f"1 {token_in} is > {ratio} ({token_out}), got {item.price}"
