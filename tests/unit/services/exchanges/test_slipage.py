import pytest
from decimal import Decimal
from alphaswarm.services.exchanges.base import Slippage


def test_slippage_init_valid() -> None:
    slippage = Slippage(100)  # 1%
    assert slippage.bps == 100


def test_slippage_init_invalid() -> None:
    with pytest.raises(ValueError, match="Slippage must be between 0 and 10000 basis points"):
        Slippage(-1)

    with pytest.raises(ValueError, match="Slippage must be between 0 and 10000 basis points"):
        Slippage(10001)


def test_from_percentage() -> None:
    # Test with float
    slippage = Slippage.from_percentage(1.0)  # 1%
    assert slippage.bps == 100

    # Test with Decimal
    slippage = Slippage.from_percentage(Decimal("1.5"))  # 1.5%
    assert slippage.bps == 150


def test_to_percentage() -> None:
    slippage = Slippage(150)  # 1.5%
    assert slippage.to_percentage() == 1.5


def test_to_multiplier() -> None:
    slippage = Slippage(100)  # 1%
    assert slippage.to_multiplier() == Decimal("0.99")

    slippage = Slippage(50)  # 0.5%
    assert slippage.to_multiplier() == Decimal("0.995")


def test_calculate_minimum_amount() -> None:
    slippage = Slippage(100)  # 1%

    # Test with integer
    assert slippage.calculate_minimum_amount(1000) == 990

    # Test with str
    assert slippage.calculate_minimum_amount("1000.0") == 990

    # Test with Decimal
    assert slippage.calculate_minimum_amount(Decimal("1000")) == 990


def test_string_representations() -> None:
    slippage = Slippage(100)

    # Test __str__
    assert str(slippage) == "100 bps"

    # Test __repr__
    assert repr(slippage) == "Slippage(bps=100)"


def test_edge_cases() -> None:
    # Test 0% slippage
    slippage = Slippage(0)
    assert slippage.to_multiplier() == Decimal(1)
    assert slippage.calculate_minimum_amount(1000) == 1000

    # Test 100% slippage
    slippage = Slippage(10000)
    assert slippage.to_multiplier() == Decimal(0)
    assert slippage.calculate_minimum_amount(1000) == 0
