from decimal import Decimal

import pytest

from alphaswarm.config import Config
from alphaswarm.services.chains import EVMClient
from alphaswarm.tools.exchanges import ExecuteTokenSwapTool


@pytest.fixture
def token_swap_tool(default_config: Config) -> ExecuteTokenSwapTool:
    return ExecuteTokenSwapTool(default_config)


@pytest.fixture
def sepolia_client(default_config: Config) -> EVMClient:
    return EVMClient(default_config.get_chain_config("ethereum_sepolia"))


@pytest.mark.skip("Requires a founded wallet. Run manually")
def test_token_swap_tool(token_swap_tool: ExecuteTokenSwapTool, sepolia_client: EVMClient) -> None:
    weth = sepolia_client.get_token_info_by_name("WETH")
    usdc = sepolia_client.get_token_info_by_name("USDC")
    pool_address = "0x3289680dD4d6C10bb19b899729cda5eEF58AEfF1"
    result = token_swap_tool.forward(
        token_out=weth.address,
        token_in=usdc.address,
        amount_in=Decimal(1),
        chain="ethereum_sepolia",
        pool=pool_address,
        dex_type="uniswap_v3",
    )
    print(result)
