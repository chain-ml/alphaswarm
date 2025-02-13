import pytest

from alphaswarm.config import Config
from alphaswarm.tools import GetTokenAddress


@pytest.fixture
def tool(default_config: Config) -> GetTokenAddress:
    return GetTokenAddress(default_config)


@pytest.mark.parametrize(
    "symbol,expected_address,chain",
    [
        ("WETH", "0x4200000000000000000000000000000000000006", "base"),
        ("WETH", "0xfff9976782d46cc05630d1f6ebab18b2324d6b14", "ethereum_sepolia"),
        ("WETH", "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", "ethereum"),
        ("GIGA", "63LfDmNb3MQ8mw9MtZ2To9bEA2M71kZUUGq5tiJxcqj9", "solana"),
    ],
)
def test_get_token_address(symbol: str, expected_address: str, chain: str, tool: GetTokenAddress) -> None:
    result = tool.forward(symbol, chain)
    assert result == expected_address


def test_get_token_address__raises_exception__if_symbol_not_found(tool: GetTokenAddress) -> None:
    with pytest.raises(ValueError):
        tool.forward("NotAToken", "ethereum")


def test_get_token_address__raises_exception__if_invalid_chain(tool: GetTokenAddress) -> None:
    with pytest.raises(ValueError) as e:
        tool.forward("WETH", "NotAChain")

    assert str(e.value).startswith("Unknown chain! Configured chains: ")
