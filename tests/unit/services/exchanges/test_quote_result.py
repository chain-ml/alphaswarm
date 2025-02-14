from decimal import Decimal

from alphaswarm.config import TokenInfo
from alphaswarm.services.exchanges import QuoteResult


def test_quote_result_str() -> None:
    token_info = TokenInfo(symbol="TOKEN", address="123", decimals=18, chain="chain")
    value = QuoteResult(
        quote="my private quote details",
        amount_in=Decimal(1),
        amount_out=Decimal(1),
        token_in=token_info,
        token_out=token_info,
    )

    assert value.quote not in str(value)
