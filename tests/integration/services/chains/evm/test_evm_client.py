import pytest
from eth_typing import ChecksumAddress

from alphaswarm.config import Config
from alphaswarm.services.chains import EVMClient


@pytest.fixture
def evm_client(default_config: Config, chain: str) -> EVMClient:
    return EVMClient(chain_config=default_config.get_chain_config(chain))


@pytest.fixture
def binance_hot_wallet() -> ChecksumAddress:
    return EVMClient.to_checksum_address("0xF977814e90dA44bFA03b6295A0616a897441aceC")


main_net_chains = ["ethereum", "base"]
test_net_chains = ["ethereum_sepolia", "base_sepolia"]
all_chains = main_net_chains + test_net_chains


@pytest.mark.parametrize("chain", all_chains)
def test_get_native_token_balance(evm_client: EVMClient, chain: str, binance_hot_wallet: ChecksumAddress) -> None:
    balance_native = evm_client.get_native_balance(binance_hot_wallet)
    assert balance_native > 1


@pytest.mark.parametrize("chain", main_net_chains)
def test_get_erc20_token_balance(evm_client: EVMClient, chain: str, binance_hot_wallet: ChecksumAddress) -> None:

    erc20_balance = evm_client.get_token_balance("USDC", binance_hot_wallet)
    assert erc20_balance > 1


@pytest.mark.parametrize("chain", all_chains)
def test_get_block_latest(evm_client: EVMClient, chain: str) -> None:
    result = evm_client.get_block_latest()
    assert result["timestamp"] > 0


@pytest.mark.parametrize("chain", all_chains)
def test_get_transaction_count(evm_client: EVMClient, chain: str, binance_hot_wallet: ChecksumAddress) -> None:
    result = evm_client._client.eth.get_transaction_count(binance_hot_wallet)
    print(result)
