from decimal import Decimal
from typing import List, Optional, Tuple

import pytest

from alphaswarm.config import Config, TokenInfo
from alphaswarm.exchanges import DEXClient, DEXFactory
from alphaswarm.exchanges.base import SwapResult


class MockDex(DEXClient):
    def swap(
        self, base_token: TokenInfo, quote_token: TokenInfo, quote_amount: float, slippage_bps: int = 100
    ) -> SwapResult:
        raise NotImplementedError("For test only")

    def get_markets_for_tokens(self, tokens: List[TokenInfo]) -> List[Tuple[TokenInfo, TokenInfo]]:
        raise NotImplementedError("For test only")

    def get_token_price(self, base_token: TokenInfo, quote_token: TokenInfo) -> Optional[Decimal]:
        raise NotImplementedError("For test only")

    def __init__(self, config, chain: str):
        super().__init__(config, chain)


def test_register(default_config: Config) -> None:
    with pytest.raises(ValueError):
        DEXFactory.create("test_dex", default_config, "ethereum")

    factory = DEXFactory()
    factory.register_dex("test_dex", MockDex)

    assert factory.create("test_dex", default_config, "ethereum") is not None
    assert DEXFactory.create("test_dex", default_config, "ethereum") is not None

    new_factory = DEXFactory()
    assert new_factory.create("test_dex", default_config, "ethereum") is not None
