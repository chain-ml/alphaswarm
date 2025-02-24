from decimal import Decimal

import pytest
from web3.types import Wei

from alphaswarm.core.token import BaseUnit, TokenAmount, TokenInfo


@pytest.fixture
def eth_token() -> TokenInfo:
    return TokenInfo(
        symbol="ETH",
        address="0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        decimals=18,
        chain="ethereum",
        is_native=True,
    )


@pytest.fixture
def usdc_token() -> TokenInfo:
    return TokenInfo(symbol="USDC", address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", decimals=6, chain="ethereum")


def test_token_amount_init(eth_token: TokenInfo) -> None:
    amount = TokenAmount(eth_token, Decimal("1.5"))
    assert amount.token_info == eth_token
    assert amount.value == Decimal("1.5")


def test_token_amount_is_zero(eth_token: TokenInfo) -> None:
    zero_amount = TokenAmount(eth_token, Decimal("0"))
    non_zero_amount = TokenAmount(eth_token, Decimal("1.5"))

    assert zero_amount.is_zero is True
    assert non_zero_amount.is_zero is False


def test_token_amount_str_formatting(eth_token: TokenInfo) -> None:
    amount = TokenAmount(eth_token, Decimal("1.23456789"))
    assert str(amount) == "1.23456789 ETH"

    large_amount = TokenAmount(eth_token, Decimal("1234567.89"))
    assert str(large_amount) == "1,234,567.89000000 ETH"


def test_token_amount_equality(eth_token: TokenInfo, usdc_token: TokenInfo) -> None:
    amount1 = TokenAmount(eth_token, Decimal("1.5"))
    amount2 = TokenAmount(eth_token, Decimal("1.5"))
    different_token = TokenAmount(usdc_token, Decimal("1.5"))
    different_amount = TokenAmount(eth_token, Decimal("2.0"))

    assert amount1 == amount2
    assert amount1 != different_token
    assert amount1 != different_amount
    assert amount1 != "not a token amount"


def test_token_amount_comparison(eth_token: TokenInfo) -> None:
    amount1 = TokenAmount(eth_token, Decimal("1.5"))
    amount2 = TokenAmount(eth_token, Decimal("2.0"))
    amount3 = TokenAmount(eth_token, Decimal("1.5"))

    assert amount1 < amount2
    assert amount1 <= amount2
    assert amount2 > amount1
    assert amount2 >= amount1
    assert amount1 <= amount3
    assert amount1 >= amount3


def test_token_amount_comparison_different_tokens(eth_token: TokenInfo, usdc_token: TokenInfo) -> None:
    eth_amount = TokenAmount(eth_token, Decimal("1.5"))
    usdc_amount = TokenAmount(usdc_token, Decimal("1.5"))

    with pytest.raises(ValueError, match="Cannot compare different tokens"):
        _ = eth_amount < usdc_amount

    with pytest.raises(ValueError, match="Cannot compare different tokens"):
        _ = eth_amount > usdc_amount


def test_token_amount_base_units(eth_token: TokenInfo, usdc_token: TokenInfo) -> None:
    # Test ETH (18 decimals)
    eth_amount = TokenAmount(eth_token, Decimal("1.5"))
    assert eth_amount.base_units == BaseUnit(1500000000000000000)

    # Test USDC (6 decimals)
    usdc_amount = TokenAmount(usdc_token, Decimal("1.5"))
    assert usdc_amount.base_units == BaseUnit(1500000)


def test_token_info_convert_base_units(eth_token: TokenInfo) -> None:
    # Test converting to base units
    base_units = eth_token.convert_to_base_units(Decimal("1.5"))
    assert base_units == BaseUnit(1500000000000000000)

    # Test converting from base units
    wei_amount = Wei(1500000000000000000)
    decimal_amount = eth_token.convert_from_base_units(wei_amount)
    assert decimal_amount == Decimal("1.5")


def test_token_info_amount_creation(eth_token: TokenInfo) -> None:
    # Test creating amount from decimal
    amount1 = eth_token.to_amount(Decimal("1.5"))
    assert amount1.value == Decimal("1.5")
    assert amount1.token_info == eth_token

    # Test creating zero amount
    zero_amount = eth_token.to_zero_amount()
    assert zero_amount.value == Decimal("0")
    assert zero_amount.is_zero is True

    # Test creating amount from base units
    base_amount = eth_token.to_amount_from_base_units(Wei(1500000000000000000))
    assert base_amount.value == Decimal("1.5")


def test_token_info_equality(eth_token: TokenInfo) -> None:
    same_token = TokenInfo(symbol="ETH", address=eth_token.address, decimals=18, chain="ethereum", is_native=True)
    different_chain = TokenInfo(symbol="ETH", address=eth_token.address, decimals=18, chain="base", is_native=True)
    different_address = TokenInfo(
        symbol="ETH",
        address="0x1234567890123456789012345678901234567890",
        decimals=18,
        chain="ethereum",
        is_native=True,
    )

    assert eth_token == same_token
    assert eth_token != different_chain
    assert eth_token != different_address
    assert eth_token != "not a token info"


def test_token_info_ethereum_factory() -> None:
    eth = TokenInfo.Ethereum()
    assert eth.symbol == "ETH"
    assert eth.decimals == 18
    assert eth.is_native is True
    assert eth.chain == "ethereum"
    assert eth.address == ""


def test_token_info_address_to_path(eth_token: TokenInfo, usdc_token: TokenInfo) -> None:
    # Test normal address
    assert usdc_token.address_to_path() == "A0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

    # Test address with 0x prefix
    token = TokenInfo(symbol="TEST", address="0x1234", decimals=18, chain="ethereum")
    assert token.address_to_path() == "0000000000000000000000000000000000001234"

    # Test empty address
    empty_addr_token = TokenInfo(symbol="TEST", address="", decimals=18, chain="ethereum")
    assert empty_addr_token.address_to_path() == "0" * 40


def test_token_info_checksum_address(usdc_token: TokenInfo) -> None:
    # Test converting to checksum address
    assert usdc_token.checksum_address == "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

    # Test with lowercase address
    token = TokenInfo(
        symbol="TEST", address="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", decimals=18, chain="ethereum"
    )
    assert token.checksum_address == "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"


def test_token_info_validation() -> None:
    # Test valid token creation
    token = TokenInfo(
        symbol="TEST", address="0x1234567890123456789012345678901234567890", decimals=18, chain="ethereum"
    )
    assert token.symbol == "TEST"
    assert token.decimals == 18

    # Test with minimum required fields
    min_token = TokenInfo(symbol="MIN", address="", decimals=6, chain="ethereum")
    assert min_token.is_native is False


def test_token_info_str_representation(eth_token: TokenInfo) -> None:
    # Test string representation includes key information
    token_str = str(eth_token)
    assert eth_token.symbol in token_str
    assert eth_token.address in token_str
    assert eth_token.chain in token_str
