import pytest

from alphaswarm.config import Config, WalletInfo
from alphaswarm.services.alchemy import AlchemyClient
from alphaswarm.services.chains import EVMClient, SolanaClient
from alphaswarm.services.portfolio.portfolio import Portfolio, PortfolioEvm, PortfolioSolana


@pytest.mark.skip("Need wallet")
def test_portfolio_get_balances(default_config: Config, alchemy_client: AlchemyClient) -> None:
    eth_config = default_config.get_chain_config("ethereum")
    eth_sepolia_config = default_config.get_chain_config("ethereum_sepolia")
    solana_config = default_config.get_chain_config("solana")
    portfolios = [
        PortfolioEvm(WalletInfo.from_chain_config(eth_config), EVMClient(eth_config), alchemy_client),
        PortfolioEvm(WalletInfo.from_chain_config(eth_sepolia_config), EVMClient(eth_sepolia_config), alchemy_client),
        PortfolioSolana(WalletInfo.from_chain_config(solana_config), SolanaClient(solana_config)),
    ]

    portfolio = Portfolio(portfolios)
    result = portfolio.get_token_balances()
    assert len(result) > 3
