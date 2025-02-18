from datetime import datetime, timedelta, timezone

import pytest

from alphaswarm.config import ChainConfig, Config
from alphaswarm.services.alchemy.alchemy_client import AlchemyClient

main_net_chains = ["ethereum", "base"]
test_net_chains = ["ethereum_sepolia", "base_sepolia"]
all_chains = main_net_chains + test_net_chains


@pytest.fixture
def chain_config(default_config: Config, chain: str) -> ChainConfig:
    return default_config.get_chain_config(chain=chain)


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


@pytest.mark.parametrize("chain", all_chains)
@pytest.mark.skip("Needs a wallet")
def test_get_incoming_transfers(alchemy_client: AlchemyClient, chain_config: ChainConfig, chain: str) -> None:
    # Test outgoing transfers
    transfers = alchemy_client.get_transfers(
        wallet=chain_config.wallet_address, chain=chain_config.chain, incoming=True
    )

    assert len(transfers) > 0
    assert transfers[0].from_address.lower() == chain_config.wallet_address.lower()


@pytest.mark.parametrize("chain", all_chains)
@pytest.mark.skip("Needs a wallet")
def test_get_outcoming_transfers(alchemy_client: AlchemyClient, chain_config: ChainConfig, chain: str) -> None:
    # Test outgoing transfers
    transfers = alchemy_client.get_transfers(
        wallet=chain_config.wallet_address, chain=chain_config.chain, incoming=False
    )

    assert len(transfers) > 0
    assert transfers[0].to_address.lower() == chain_config.wallet_address.lower()


@pytest.mark.parametrize("chain", all_chains)
@pytest.mark.skip("Needs a wallet")
def test_get_all_transfers(alchemy_client: AlchemyClient, chain_config: ChainConfig, chain: str) -> None:
    # Test outgoing transfers
    in_transfers = alchemy_client.get_transfers(
        wallet=chain_config.wallet_address, chain=chain_config.chain, incoming=True
    )
    out_transfers = alchemy_client.get_transfers(
        wallet=chain_config.wallet_address, chain=chain_config.chain, incoming=False
    )


def test_get_transfers_invalid_chain(alchemy_client: AlchemyClient) -> None:
    with pytest.raises(ValueError, match="Unsupported chain invalid_chain"):
        alchemy_client.get_transfers(wallet="0x123", chain="invalid_chain", incoming=False)


@pytest.mark.parametrize("chain", all_chains)
@pytest.mark.skip("Needs a wallet")
def test_get_token_balances(alchemy_client: AlchemyClient, chain_config: ChainConfig, chain: str) -> None:
    # Test outgoing transfers
    balances = alchemy_client.get_token_balances(wallet=chain_config.wallet_address, chain=chain_config.chain)

    assert len(balances) > 0
    assert balances[0].value > 0


def test_get_token_balances_invalid_chain(alchemy_client: AlchemyClient) -> None:
    with pytest.raises(ValueError, match="Unsupported chain invalid_chain"):
        alchemy_client.get_transfers(
            wallet="0x123",
            chain="invalid_chain",
        )
