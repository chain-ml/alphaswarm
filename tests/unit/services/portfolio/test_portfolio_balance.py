from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from alphaswarm.core.token import TokenAmount, TokenInfo
from alphaswarm.services.portfolio.portfolio import PortfolioBalance


@pytest.fixture
def eth_token() -> TokenInfo:
    return TokenInfo(
        symbol="WETH",
        address="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        decimals=18,
        chain="ethereum",
    )


@pytest.fixture
def usdc_token() -> TokenInfo:
    return TokenInfo(symbol="USDC", address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", decimals=6, chain="ethereum")


@pytest.fixture
def eth_balance(eth_token: TokenInfo) -> TokenAmount:
    return TokenAmount(eth_token, Decimal("1.5"))


@pytest.fixture
def usdc_balance(usdc_token: TokenInfo) -> TokenAmount:
    return TokenAmount(usdc_token, Decimal("1000"))


@pytest.fixture
def portfolio_balance(eth_balance: TokenAmount, usdc_balance: TokenAmount) -> PortfolioBalance:
    return PortfolioBalance([eth_balance, usdc_balance])


def test_init_creates_balance_map(
    portfolio_balance: PortfolioBalance, eth_balance: TokenAmount, usdc_balance: TokenAmount
) -> None:
    assert portfolio_balance.get_token_balance(eth_balance.token_info.address) == eth_balance
    assert portfolio_balance.get_token_balance(usdc_balance.token_info.address) == usdc_balance


def test_timestamp_is_set_on_init(portfolio_balance: PortfolioBalance) -> None:
    assert isinstance(portfolio_balance.timestamp, datetime)
    assert portfolio_balance.timestamp.tzinfo == UTC


def test_age_seconds(portfolio_balance: PortfolioBalance) -> None:
    with patch("alphaswarm.services.portfolio.portfolio.datetime") as mock_datetime:
        creation_time = datetime(2024, 1, 1, tzinfo=UTC)
        current_time = creation_time + timedelta(seconds=30)

        mock_datetime.now.return_value = current_time
        mock_datetime.now.side_effect = lambda tz: current_time

        with patch.object(portfolio_balance, "_timestamp", creation_time):
            assert portfolio_balance.age_seconds() == 30.0


def test_has_token(portfolio_balance: PortfolioBalance, eth_token: TokenInfo, usdc_token: TokenInfo) -> None:
    assert portfolio_balance.has_token(eth_token.address) is True
    assert portfolio_balance.has_token(usdc_token.address) is True
    assert portfolio_balance.has_token("0x0000000000000000000000000000000000000000") is False


def test_get_token_balance(
    portfolio_balance: PortfolioBalance, eth_balance: TokenAmount, usdc_balance: TokenAmount
) -> None:
    assert portfolio_balance.get_token_balance(eth_balance.token_info.address) == eth_balance
    assert portfolio_balance.get_token_balance(usdc_balance.token_info.address) == usdc_balance
    assert portfolio_balance.get_token_balance("0x0000000000000000000000000000000000000000") is None


def test_get_balance_value(portfolio_balance: PortfolioBalance, eth_token: TokenInfo, usdc_token: TokenInfo) -> None:
    assert portfolio_balance.get_balance_value(eth_token.address) == Decimal("1.5")
    assert portfolio_balance.get_balance_value(usdc_token.address) == Decimal("1000")
    assert portfolio_balance.get_balance_value("0x0000000000000000000000000000000000000000") == Decimal("0")


def test_get_all_balances(
    portfolio_balance: PortfolioBalance, eth_balance: TokenAmount, usdc_balance: TokenAmount
) -> None:
    balances = portfolio_balance.get_all_balances()
    assert len(balances) == 2
    assert eth_balance in balances
    assert usdc_balance in balances


def test_get_non_zero_balances(
    portfolio_balance: PortfolioBalance, eth_token: TokenInfo, usdc_token: TokenInfo
) -> None:
    zero_token = eth_token.to_zero_amount()
    portfolio = PortfolioBalance([zero_token, usdc_token.to_amount(Decimal("10"))])

    balances = portfolio.get_non_zero_balances()
    assert len(balances) == 1
    assert balances[0].token_info.address == usdc_token.address


def test_total_tokens(portfolio_balance: PortfolioBalance) -> None:
    assert portfolio_balance.total_tokens == 2


def test_non_zero_tokens(portfolio_balance: PortfolioBalance, eth_token: TokenInfo, usdc_token: TokenInfo) -> None:
    zero_token = eth_token.to_zero_amount()
    portfolio = PortfolioBalance([zero_token, usdc_token.to_amount(Decimal("10"))])

    assert portfolio.non_zero_tokens == 1


def test_has_enough_balance_of(
    portfolio_balance: PortfolioBalance, eth_token: TokenInfo, usdc_token: TokenInfo
) -> None:
    # Test with sufficient balance
    spendable_amount = TokenAmount(eth_token, Decimal("1.0"))
    assert portfolio_balance.has_enough_balance_of(spendable_amount) is True

    # Test with exact balance
    exact_amount = TokenAmount(eth_token, Decimal("1.5"))
    assert portfolio_balance.has_enough_balance_of(exact_amount) is True

    # Test with insufficient balance
    too_much = TokenAmount(eth_token, Decimal("2.0"))
    assert portfolio_balance.has_enough_balance_of(too_much) is False

    # Test with non-existent token
    unknown_token = TokenInfo(
        symbol="UNKNOWN", address="0x1234567890123456789012345678901234567890", decimals=18, chain="ethereum"
    )
    unknown_amount = TokenAmount(unknown_token, Decimal("1.0"))
    assert portfolio_balance.has_enough_balance_of(unknown_amount) is False
