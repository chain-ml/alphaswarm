from alphaswarm.config import Config
from alphaswarm.services.exchanges.jupiter.jupiter import JupiterClient


def test_get_token_price(default_config: Config) -> None:
    chain = "solana"
    chain_config = default_config.get_chain_config(chain)
    client = JupiterClient.from_config(default_config, chain)

    # Get token info and create TokenInfo object
    tokens_config = chain_config.tokens
    giga = tokens_config["GIGA"]
    sol = tokens_config["SOL"]

    price = client.get_token_price(giga, sol)
    assert price > 0
