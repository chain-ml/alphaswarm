from alphaswarm.services.chains import EVMClient, SolanaClient
from alphaswarm.config import Config
from alphaswarm.services.chains.evm import ERC20Contract


def test_get_token_info(default_config: Config) -> None:
    """Test getting token info for USDC on ethereum."""
    chain = "ethereum"
    client = EVMClient(chain_config=default_config.get_chain_config(chain))
    usdc_address = EVMClient.to_checksum_address("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")

    token_info = client.get_token_info(usdc_address)
    print(token_info)

    assert token_info.address == usdc_address
    assert token_info.decimals == 6  # USDC has 6 decimals
    assert token_info.symbol == "USDC"
    assert token_info.chain == chain
    assert not token_info.is_native


def test_get_solana_balance(default_config: Config) -> None:
    """Test getting balance for a known Solana wallet."""
    client = SolanaClient(default_config.get_chain_config("solana"))

    # Test wallet with known SOL balance
    # Using a known active Solana wallet (Binance hot wallet)
    wallet = "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E"
    balance = client.get_token_balance("SOL", wallet)

    assert balance is not None
    assert balance > 0
    print(f"Wallet balance: {balance}")


def test_get_base_balance(default_config: Config) -> None:
    client = EVMClient(chain_config=default_config.get_chain_config("base"))

    # Test wallet with known balance
    # Using a known active Base wallet (Binance hot wallet)
    wallet = client.to_checksum_address("0xF977814e90dA44bFA03b6295A0616a897441aceC")
    token_symbol = "USDC"
    balance = client.get_token_balance(token_symbol, wallet)

    assert balance is not None
    assert balance > 0
    print(f"Wallet balance: {balance}")


def test_get_contract_balance(default_config: Config) -> None:
    client = EVMClient(default_config.get_chain_config("base"))
    contract = ERC20Contract(client, client.get_token_info_by_name("USDC").checksum_address)
    # Using a known active Base wallet (Binance hot wallet)
    value = contract.get_balance(EVMClient.to_checksum_address("0xF977814e90dA44bFA03b6295A0616a897441aceC"))
    assert value > 0


def test_get_eth_balance(default_config: Config) -> None:
    """Test getting balance for a known USDC wallet."""
    client = EVMClient(chain_config=default_config.get_chain_config("ethereum"))

    # Test wallet with known balance
    # Using a known active USDC wallet (Binance hot wallet)
    wallet = client.to_checksum_address("0xF977814e90dA44bFA03b6295A0616a897441aceC")
    token_symbol = "USDC"
    balance = client.get_token_balance(token_symbol, wallet)

    assert balance is not None
    assert balance > 0
    print(f"Wallet balance: {balance}")


def test_get_native_token(default_config: Config) -> None:
    client = EVMClient(chain_config=default_config.get_chain_config("ethereum"))
    wallet = client.to_checksum_address("0xF977814e90dA44bFA03b6295A0616a897441aceC")
    balance_native = client.get_native_balance(wallet)

    assert balance_native > 0
