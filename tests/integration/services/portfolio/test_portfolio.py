import pytest

from alphaswarm.config import ChainConfig, Config, WalletInfo
from alphaswarm.services.alchemy import AlchemyClient
from alphaswarm.services.chains import EVMClient
from alphaswarm.services.portfolio import Portfolio
from alphaswarm.services.portfolio.portfolio import PortfolioEvm


@pytest.fixture
def eth_sepolia_config(default_config: Config) -> ChainConfig:
    return default_config.get_chain_config("ethereum_sepolia")


@pytest.fixture
def eth_sepolia_portfolio(eth_sepolia_config: ChainConfig, alchemy_client: AlchemyClient) -> PortfolioEvm:
    return PortfolioEvm(WalletInfo.from_chain_config(eth_sepolia_config), EVMClient(eth_sepolia_config), alchemy_client)


@pytest.fixture
def evm_portfolio(chain: str, default_config: Config, alchemy_client: AlchemyClient) -> PortfolioEvm:
    chain_config = default_config.get_chain_config(chain)
    return PortfolioEvm(WalletInfo.from_chain_config(chain_config), EVMClient(chain_config), alchemy_client)


@pytest.mark.skip("Need wallet")
def test_portfolio_get_balances(default_config: Config, alchemy_client: AlchemyClient) -> None:
    portfolio = Portfolio.from_config(default_config)
    result = portfolio.get_token_balances()
    assert len(result.get_non_zero_balances()) > 3


chains = ["ethereum", "ethereum_sepolia", "base"]


@pytest.mark.parametrize("chain", chains)
@pytest.mark.skip("Need wallet")
def test_portfolio_get_positions(chain: str, evm_portfolio: PortfolioEvm) -> None:
    result = evm_portfolio.get_positions()
    for item in result:
        print(item.to_short_string())
