from datetime import datetime, timedelta, timezone

import pytest

from alphaswarm.config import ChainConfig, Config
from alphaswarm.services.alchemy.alchemy_client import AlchemyClient


@pytest.fixture
def eth_sepolia_config(default_config: Config) -> ChainConfig:
    return default_config.get_chain_config(chain="ethereum_sepolia")


def test_historical_prices_by_symbol(alchemy_client: AlchemyClient) -> None:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=1)
    result = alchemy_client.get_historical_prices_by_symbol(
        symbol="USDC", start_time=start, end_time=end, interval="1h"
    )

    assert result is not None
    assert result.symbol == "USDC"
    assert 24 <= len(result.data) <= 25
    assert result.data[0].value > 0.1
    assert result.data[0].timestamp >= start


def test_historical_prices_by_address(alchemy_client: AlchemyClient) -> None:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=1)
    address = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
    network = "eth-mainnet"
    result = alchemy_client.get_historical_prices_by_address(
        address=address, network=network, start_time=start, end_time=end, interval="1h"
    )

    assert result is not None
    assert result.address == address
    assert result.network == network
    assert 24 <= len(result.data) <= 25
    assert result.data[0].value > 0.1
    assert result.data[0].timestamp >= start


@pytest.mark.skip("Needs a wallet")
def test_get_incoming_transfer(alchemy_client: AlchemyClient, eth_sepolia_config: ChainConfig) -> None:
    # Test outgoing transfers
    transfers = alchemy_client.get_transfers(
        wallet=eth_sepolia_config.wallet_address, chain=eth_sepolia_config.chain, incoming=False
    )

    assert len(transfers) > 0
    assert transfers[0].from_address.lower() == eth_sepolia_config.wallet_address.lower()


@pytest.mark.skip("Needs a wallet")
def test_get_outcoming_transfer(alchemy_client: AlchemyClient, eth_sepolia_config: ChainConfig) -> None:
    # Test outgoing transfers
    transfers = alchemy_client.get_transfers(
        wallet=eth_sepolia_config.wallet_address, chain=eth_sepolia_config.chain, incoming=True
    )

    assert len(transfers) > 0
    assert transfers[0].to_address.lower() == eth_sepolia_config.wallet_address.lower()
