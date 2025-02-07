from decimal import Decimal

import pytest

from alphaswarm.config import Config
from alphaswarm.tools.exchanges import ExecuteTokenSwapTool


@pytest.fixture
def token_swap_tool(default_config: Config) -> ExecuteTokenSwapTool:
    return ExecuteTokenSwapTool(default_config)


@pytest.mark.skip("Requires a founded wallet. Run manually")
def test_token_swap_tool(token_swap_tool: ExecuteTokenSwapTool) -> None:
    result = token_swap_tool.forward(token_quote="WETH", token_base="USDC", amount=Decimal(1), chain="ethereum_sepolia")
    print(result)
