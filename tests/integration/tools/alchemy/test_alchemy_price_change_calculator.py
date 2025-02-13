from alphaswarm.services.alchemy import AlchemyClient
from alphaswarm.tools.alchemy.alchemy_price_change import TokenPriceChangeCalculator


def test_get_price_change(alchemy_client: AlchemyClient) -> None:
    tool = TokenPriceChangeCalculator(alchemy_client)
    result = tool.forward(
        token_address="0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",  # WBTC
        frequency="5m",
        n_samples=2,
        network="eth-mainnet",
    )

    assert abs(result.percent_change) > 0
