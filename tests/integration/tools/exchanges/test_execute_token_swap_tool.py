from decimal import Decimal

import pytest

from alphaswarm.config import Config
from alphaswarm.services.chains import EVMClient
from alphaswarm.tools.exchanges import ExecuteTokenSwap, GetTokenPrice


@pytest.fixture
def token_quote_tool(default_config: Config) -> GetTokenPrice:
    return GetTokenPrice(default_config)


@pytest.fixture
def token_swap_tool(default_config: Config) -> ExecuteTokenSwap:
    return ExecuteTokenSwap(default_config)


@pytest.fixture
def sepolia_client(default_config: Config) -> EVMClient:
    return EVMClient(default_config.get_chain_config("ethereum_sepolia"))


@pytest.mark.skip("Requires a founded wallet. Run manually")
def test_token_swap_tool(
    token_quote_tool: GetTokenPrice, token_swap_tool: ExecuteTokenSwap, sepolia_client: EVMClient
) -> None:
    weth = sepolia_client.get_token_info_by_name("WETH")
    usdc = sepolia_client.get_token_info_by_name("USDC")
    amount_in = Decimal(10)

    quotes = token_quote_tool.forward(
        token_out=weth.address,
        token_in=usdc.address,
        amount_in=str(amount_in),
        chain=sepolia_client.chain,
        dex_type="uniswap_v3",
    )
    assert len(quotes.quotes) == 1
    result = token_swap_tool.forward(quote=quotes.quotes[0])
    print(result)
    assert result.success
    assert result.amount_out < amount_in
