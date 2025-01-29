from _pytest.fixtures import fixture

from alphaswarm.services.alchemy import AlchemyClient
from alphaswarm.tools.alchemy.alchemy_price_history import AlchemyPriceHistory


@fixture
def tool(alchemy_client: AlchemyClient) -> AlchemyPriceHistory:
    return AlchemyPriceHistory(alchemy_client)


def test_get_price_history_by_symbol(tool: AlchemyPriceHistory) -> None:
    result = tool.forward(address_or_symbol="USDC", history=1)

    assert result is not None
    assert result[0].value > 0.1


def test_get_price_history_by_address(tool: AlchemyPriceHistory) -> None:
    usdc_address = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    result = tool.forward(address_or_symbol=usdc_address, network="base-mainnet", history=1)
    assert result is not None
    assert result[0].value > 0.1
