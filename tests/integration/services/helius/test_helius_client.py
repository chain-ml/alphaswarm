import pytest

from alphaswarm.config import Config
from alphaswarm.services.chains import SolanaClient
from alphaswarm.services.helius.helius_client import HeliusClient


@pytest.fixture
def client(default_config: Config) -> HeliusClient:
    return HeliusClient.from_env()


@pytest.fixture
def wallet_address(default_config: Config) -> str:
    return default_config.get_chain_config("solana").wallet_address


@pytest.fixture
def solana_client(default_config: Config) -> SolanaClient:
    return SolanaClient(default_config.get_chain_config("solana"))


@pytest.mark.skip("Requires an API KEY and a wallet address")
def test_get_signatures_for_wallet(client: HeliusClient, wallet_address: str) -> None:
    signature_result = client.get_signatures_for_address(wallet_address)
    assert len(signature_result) > 0


@pytest.mark.skip("Requires an API KEY and a wallet address")
def test_get_transactions(client: HeliusClient, wallet_address: str) -> None:
    signatures = [
        "2ayqz3XdE9W8uoMoraqqvepZySwA9kaAhNKWF4GRxeLM9N6tQuwjnUnZLnPbng263wSpMp8FyFmbK64PSUbCRpsg",
        "2kFxpa3fCtjL3UWBKdhpCcdVWZ2VH9A2YF3mEFxDwNSW3Q2r5AdZL4ZRSeyGM2da3t189rSkcBSFyfHse29A6J3K",
        "3C3g5dk2MPDcmJD6fvjkSQn8EYF5U1cyxywkZMRsiSWfifTM77NJXLgtHLEd5iXqFX2LQQEzrTr6gwx1xoNMy8uX",
    ]

    result = client.get_transactions(signatures)
    assert [item.signature for item in result] == signatures
    assert all(len(item.token_transfers) > 0 for item in result)
