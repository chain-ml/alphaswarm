import pytest

from alphaswarm.config import Config
from alphaswarm.services.alchemy import AlchemyClient
from alphaswarm.services.portfolio import Portfolio


@pytest.mark.skip("Need wallet")
def test_portfolio_get_balances(default_config: Config, alchemy_client: AlchemyClient) -> None:
    portfolio = Portfolio.from_config(default_config)
    result = portfolio.get_token_balances()
    assert len(result) > 3
