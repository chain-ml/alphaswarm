from decimal import Decimal

import pytest

from alphaswarm.config import Config
from alphaswarm.services.chains import EVMClient
from alphaswarm.tools.core import GetTokenAddress
from alphaswarm.tools.exchanges import ExecuteTokenSwap, GetTokenPrice


@pytest.fixture
def token_address_tool(default_config: Config) -> GetTokenAddress:
    return GetTokenAddress(default_config)


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
@pytest.mark.parametrize(
    "chain,amount_in,token_in,token_out,min_amount_out,dex_type",
    [
        ("ethereum_sepolia", Decimal(10), "USDC", "WETH", Decimal("0.00001"), "uniswap_v3"),
        ("solana", Decimal("0.0001"), "SOL", "USDC", Decimal("0.001"), "jupiter"),
    ],
)
def test_token_swap_tool(
    token_address_tool: GetTokenAddress,
    token_quote_tool: GetTokenPrice,
    token_swap_tool: ExecuteTokenSwap,
    chain: str,
    amount_in: Decimal,
    token_in: str,
    token_out: str,
    min_amount_out: Decimal,
    dex_type: str,
) -> None:
    address_in = token_address_tool.forward(token_in, chain)
    address_out = token_address_tool.forward(token_out, chain)

    quotes = token_quote_tool.forward(
        token_out=address_out,
        token_in=address_in,
        amount_in=str(amount_in),
        chain=chain,
        dex_type=dex_type,
    )
    assert len(quotes.quotes) == 1
    result = token_swap_tool.forward(quote=quotes.quotes[0])
    print(result)
    assert result.amount_out > min_amount_out
