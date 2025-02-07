from __future__ import annotations
from decimal import Decimal
from typing import List, Tuple

import pytest

from alphaswarm.config import Config, TokenInfo, ChainConfig
from alphaswarm.services.exchanges import DEXClient, DEXFactory, SwapResult


class MockDex(DEXClient):
    @classmethod
    def from_config(cls, config: Config, chain: str) -> MockDex:
        return MockDex(chain_config=config.get_chain_config(chain))

    def swap(
        self, base_token: TokenInfo, quote_token: TokenInfo, quote_amount: Decimal, slippage_bps: int = 100
    ) -> SwapResult:
        raise NotImplementedError("For test only")

    def get_markets_for_tokens(self, tokens: List[TokenInfo]) -> List[Tuple[TokenInfo, TokenInfo]]:
        raise NotImplementedError("For test only")

    def get_token_price(self, base_token: TokenInfo, quote_token: TokenInfo) -> Decimal:
        raise NotImplementedError("For test only")

    def __init__(self, chain_config: ChainConfig) -> None:
        super().__init__(chain_config=chain_config)


def test_register(default_config: Config) -> None:
    with pytest.raises(ValueError):
        DEXFactory.create("test_dex", default_config, "ethereum")

    factory = DEXFactory()
    factory.register_dex("test_dex", MockDex)

    assert factory.create("test_dex", default_config, "ethereum") is not None
    assert DEXFactory.create("test_dex", default_config, "ethereum") is not None

    new_factory = DEXFactory()
    assert new_factory.create("test_dex", default_config, "ethereum") is not None
