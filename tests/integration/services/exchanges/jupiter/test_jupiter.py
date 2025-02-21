from decimal import Decimal

import pytest

from alphaswarm.config import Config
from alphaswarm.services.exchanges.jupiter.jupiter import JupiterClient


@pytest.fixture
def jupiter_client(default_config: Config) -> JupiterClient:
    return JupiterClient.from_config(default_config, "solana")


def test_get_token_price(jupiter_client: JupiterClient) -> None:
    # Get token info and create TokenInfo object
    tokens_config = jupiter_client._chain_config.tokens
    giga = tokens_config["GIGA"]
    sol = tokens_config["SOL"]

    quote = jupiter_client.get_token_price(token_out=giga, amount_in=sol.to_amount(Decimal(1)))
    assert 10000 > quote.amount_out > 1000, "A Sol is worth many thousands of GIGA."


@pytest.mark.skip("Requires a funded wallet.")
def test_swap(jupiter_client: JupiterClient) -> None:
    tokens_config = jupiter_client._chain_config.tokens
    usdc = tokens_config["usdc"]
    sol = tokens_config["SOL"]

    quote = jupiter_client.get_token_price(token_out=usdc, amount_in=sol.to_amount(Decimal("0.0001")))
    result = jupiter_client.swap(quote)

    assert result.amount_out == pytest.approx(Decimal(quote.amount_out), Decimal("0.05"))
