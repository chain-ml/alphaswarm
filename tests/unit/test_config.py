import os
from decimal import Decimal
from typing import List, Optional

import pytest
from web3.types import Wei

from alphaswarm.config import Config
from alphaswarm.core.token import TokenInfo


@pytest.fixture
def token_info() -> TokenInfo:
    return TokenInfo(symbol="TK", address="0x123", decimals=18, chain="test", is_native=False)


def test_config_default_from_env(default_config: Config) -> None:
    assert default_config.get("chain_config.ethereum.rpc_url") == os.environ.get("ETH_RPC_URL")


def address_name_pairs() -> List[tuple]:
    return [
        ("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", "WETH"),
        ("0x0000000000000000000000000000000000000000", None),
    ]


@pytest.mark.parametrize("address,name", [pair for pair in address_name_pairs() if pair[1] is not None])
def test_config_token_info(address: str, name: str, default_config: Config) -> None:
    if name is None:
        return

    actual = default_config.get_chain_config("ethereum").get_token_info(name)
    assert actual.address == "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    assert actual.decimals == 18
    assert not actual.is_native


@pytest.mark.parametrize("address,name", address_name_pairs())
def test_config_token_info_from_address_or_none(address: str, name: Optional[str], default_config: Config) -> None:
    actual = default_config.get_chain_config("ethereum").get_token_info_by_address_or_none(address)
    if name is None:
        assert actual is None
    else:
        assert actual is not None
        assert actual.address == address
        assert actual.symbol == name


@pytest.mark.parametrize("address,name", address_name_pairs())
def test_config_token_info_from_address(address: str, name: Optional[str], default_config: Config) -> None:
    if name is None:
        with pytest.raises(ValueError):
            default_config.get_chain_config("ethereum").get_token_info_by_address(address)
    else:
        actual = default_config.get_chain_config("ethereum").get_token_info_by_address(address)
        assert actual.address == address
        assert actual.symbol == name


def test_config_chain_config(default_config: Config) -> None:
    actual = default_config.get_chain_config("ethereum")
    assert not actual.tokens["WETH"].is_native
    assert actual.tokens["WETH"].symbol == "WETH"
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
    wei = token_info.convert_to_base_units(initial)
    assert Decimal(wei) == Decimal(expected)


def test_token_info_convert_from_wei(token_info: TokenInfo) -> None:
    wei: Wei = Wei(1000000000000000001)
    expected = "1.000000000000000001"
    actual = token_info.convert_from_base_units(wei)
    assert str(actual) == expected


def test_get_trading_venues_for_chain(default_config: Config) -> None:
    result = default_config.get_trading_venues_for_chain(chain="ethereum")

    assert set(result) == {"uniswap_v2", "uniswap_v3"}
