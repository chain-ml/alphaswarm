from alphaswarm.services.alchemy import AlchemyClient
from alphaswarm.tools.alchemy.alchemy_price_history import (
    AlchemyPriceHistoryBySymbol,
    AlchemyPriceHistoryByAddress,
    TokenPriceChangeCalculator
)


def test_get_price_history_by_symbol(alchemy_client: AlchemyClient) -> None:
    tool = AlchemyPriceHistoryBySymbol(alchemy_client)
    result = tool.forward(symbol="USDC", interval="5m", history=1)

    assert result.data[0].value > 0.1


def test_get_price_history_by_address(alchemy_client: AlchemyClient) -> None:
    tool = AlchemyPriceHistoryByAddress(alchemy_client)
    usdc_address = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    result = tool.forward(address=usdc_address, network="base-mainnet", interval="5m", history=1)
    assert result.data[0].value > 0.1


def test_token_price_change_calculator(alchemy_client: AlchemyClient) -> None:
    tool = TokenPriceChangeCalculator(alchemy_client)
    
    # Test with USDC on Base
    usdc_address = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    result = tool.forward(
        token_address=usdc_address,
        frequency="5m",
        n_samples=10,
        network="base-mainnet"
    )

    # Verify the structure and basic validity of the response
    assert isinstance(result["percent_change"], float)
    assert isinstance(result["start_price"], float)
    assert isinstance(result["end_price"], float)
    assert result["n_samples"] == 10
    assert result["frequency"] == "5m"
    assert result["token_address"] == usdc_address
    assert result["network"] == "base-mainnet"
    
    # Basic sanity checks
    assert result["start_price"] > 0
    assert result["end_price"] > 0
    assert -100 <= result["percent_change"] <= 1000  # Reasonable range for price changes
