from decimal import Decimal

import pytest
from pydantic import ValidationError

from alphaswarm.services.alchemy.alchemy_client import Balance


@pytest.fixture
def valid_address() -> str:
    return "0x1234567890123456789012345678901234567890"


@pytest.fixture
def valid_balance_data(valid_address) -> dict:
    return {
        "contractAddress": valid_address,
        "tokenBalance": "0x989680",
    }


@pytest.fixture
def balance(valid_balance_data) -> Balance:
    return Balance(**valid_balance_data)


@pytest.mark.parametrize(
    "hex_value, expected_decimal",
    [
        ("0x0", Decimal(0)),
        ("0xa", Decimal(10)),
        ("0x64", Decimal(100)),
        ("0x989680", Decimal(10000000)),
        ("0xde0b6b3a7640000", Decimal(1000000000000000000)),  # 1 ETH in wei
    ],
)
def test_converts_hex_to_decimal(valid_address, hex_value, expected_decimal):
    data = {"contractAddress": valid_address, "tokenBalance": hex_value}
    balance = Balance(**data)
    assert balance.value == expected_decimal


def test_converts__invalid_hex_to_decimal(valid_address):
    data = {"contractAddress": valid_address, "tokenBalance": "0xZ"}
    with pytest.raises(ValidationError):
        balance = Balance(**data)


def test_includes_error_message(valid_address):
    error_msg = "execution reverted"
    data = {"contractAddress": valid_address, "tokenBalance": "0x0", "error": error_msg}
    balance = Balance(**data)
    assert balance.error == error_msg