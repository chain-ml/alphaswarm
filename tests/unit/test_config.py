import os
from decimal import Decimal

import pytest

from alphaswarm.config import Config, TokenInfo


@pytest.fixture
def token_info():
    return TokenInfo(symbol="TK", address="0x123", decimals=18, chain="test", is_native=False)


def test_config_default_from_env(default_config: Config) -> None:
    assert default_config.get("chain_config.ethereum.rpc_url") == os.environ.get("ETH_RPC_URL")


def test_config_token_info(default_config: Config) -> None:
    actual = default_config.get_token_info(chain="ethereum", token="ETH")
    assert actual.address == "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    assert actual.decimals == 18
    assert actual.is_native


def test_config_chain_config(default_config: Config) -> None:
    actual = default_config.get_chain_config("ethereum")
    assert actual.tokens["ETH"].is_native
    assert actual.tokens["ETH"].symbol == "ETH"
    assert actual.wallet_address == os.environ.get("ETH_WALLET_ADDRESS")


def test_config_chain_config_or_none_exists(default_config: Config) -> None:
    actual = default_config.get_chain_config_or_none("ethereum")
    assert actual is not None


def test_config_chain_config_or_none__does_not_exist(default_config: Config) -> None:
    actual = default_config.get_chain_config_or_none("not a chain")
    assert actual is None


def test_config_uniswap_v3_settings(default_config: Config) -> None:
    actual = default_config.get_venue_settings_uniswap_v3()
    assert 10000 in actual.fee_tiers


def test_config_uniswap_v3(default_config: Config) -> None:
    actual = default_config.get_venue_uniswap_v3("base")
    assert "WETH_WAI" in actual.supported_pairs


def test_config_uniswap_v2(default_config: Config) -> None:
    actual = default_config.get_venue_uniswap_v2("base")
    assert "VIRTUAL_VADER" in actual.supported_pairs


def test_config_jupiter_settings(default_config: Config) -> None:
    actual = default_config.get_venue_settings_jupiter()
    assert actual.slippage_bps == 100


def test_config_jupiter(default_config: Config) -> None:
    actual = default_config.get_venue_jupiter("solana")
    assert actual.quote_api_url == "https://quote-api.jup.ag/v6/quote"


def test_token_info_convert_to_wei(token_info: TokenInfo) -> None:
    initial = Decimal("1.000000000000000001")
    expected = "1000000000000000001"
    wei = token_info.convert_to_wei(initial)
    assert str(wei) == expected


def test_token_info_convert_from_wei(token_info: TokenInfo) -> None:
    wei = 1000000000000000001
    expected = "1.000000000000000001"
    actual = token_info.convert_from_wei(wei)
    assert str(actual) == expected
