from typing import Optional

import pytest

from alphaswarm.tools.exchanges import GetTokenPriceTool
from alphaswarm.config import Config


@pytest.mark.parametrize(
    "dex,chain,token_out,token_in,min_out,max_out",
    [
        ("jupiter", "solana", "GIGA", "SOL", 1_000, 10_000),
        ("uniswap_v3", "base", "VIRTUAL", "WETH", 1_000, 10_000),
        ("uniswap_v3", "ethereum_sepolia", "USDC", "WETH", 10_000, 1_000_000),
        ("uniswap_v3", "ethereum", "USDC", "WETH", 100, 10_000),
        ("uniswap_v2", "ethereum", "USDC", "WETH", 100, 10_000),
        (None, "ethereum", "USDC", "WETH", 100, 10_000),
    ],
)
def test_get_token_price_tool(
    dex: Optional[str], chain: str, token_out: str, token_in: str, min_out: int, max_out: int, default_config: Config
) -> None:
    config = default_config
    tool = GetTokenPriceTool(config)

    chain_config = config.get_chain_config(chain)
    token_info_out = chain_config.get_token_info(token_out)
    token_info_in = chain_config.get_token_info(token_in)
    result = tool.forward(
        token_out=token_info_out.address, token_in=token_info_in.address, amount_in="1", dex_type=dex, chain=chain
    )

    assert len(result.quotes) > 0, "at least one price is expected"
    item = result.quotes[0]
    assert min_out < item.quote.amount_out < max_out
