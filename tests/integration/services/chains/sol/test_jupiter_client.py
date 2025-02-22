import pytest

from alphaswarm.services.chains.solana.jupiter_client import JupiterClient


@pytest.fixture
def client() -> JupiterClient:
    return JupiterClient()


def test_get_token_info(client: JupiterClient) -> None:
    usdc_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    token_info = client.get_token_info(usdc_address)

    assert token_info.address == usdc_address
    assert token_info.decimals == 6
    assert token_info.name == "USD Coin"
    assert token_info.symbol == "USDC"
