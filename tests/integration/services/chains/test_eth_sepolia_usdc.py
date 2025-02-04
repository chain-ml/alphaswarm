import pytest
from web3 import Web3

from alphaswarm.config import ChainConfig, Config
from alphaswarm.services.chains.evm import ERC20Contract, EVMSigner, EVMClient
from alphaswarm.services.chains.evm.evm import ZERO_CHECKSUM_ADDRESS


@pytest.fixture
def eth_sepolia_config(default_config: Config) -> ChainConfig:
    return default_config.get_chain_config("ethereum_sepolia")


@pytest.fixture
def eth_sepolia_client(default_config: Config) -> EVMClient:
    return EVMClient(default_config, "ethereum_sepolia")


@pytest.fixture
def eth_sepolia_signer(eth_sepolia_config: ChainConfig) -> EVMSigner:
    return EVMSigner(eth_sepolia_config.private_key)


@pytest.fixture
def eth_sepolia_usdc_contract(eth_sepolia_client) -> ERC20Contract:
    return ERC20Contract(eth_sepolia_client, Web3.to_checksum_address("0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238"))


def test_ecr_20_get_balance(eth_sepolia_usdc_contract: ERC20Contract) -> None:
    result = eth_sepolia_usdc_contract.get_balance(ZERO_CHECKSUM_ADDRESS)
    assert result == 0


@pytest.mark.skip("Requires a wallet with Sepolia ETH. Can run manually")
def test_approve_and_allowance(eth_sepolia_usdc_contract: ERC20Contract, eth_sepolia_signer: EVMSigner) -> None:
    spender = eth_sepolia_signer.address
    expected_allowance = 10

    tx = eth_sepolia_usdc_contract.approve(eth_sepolia_signer, spender, expected_allowance)
    print(tx)

    allowance = eth_sepolia_usdc_contract.get_allowance(eth_sepolia_signer.address, spender)
    assert allowance == expected_allowance
