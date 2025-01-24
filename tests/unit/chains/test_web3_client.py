from alphaswarm.chains.factory import Web3ClientFactory
from alphaswarm.config import Config


def test_get_token_info(default_config: Config):
    """Test getting token info for USDC on ethereum."""
    chain = "ethereum"
    client = Web3ClientFactory.get_instance().get_client(chain, default_config)
    usdc_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

    token_info = client.get_token_info(usdc_address, chain)
    print(token_info)

    assert token_info is not None
    assert token_info.address == usdc_address
    assert token_info.decimals == 6  # USDC has 6 decimals
    assert token_info.symbol == "USDC"
    assert token_info.chain == chain
    assert not token_info.is_native


def test_get_solana_balance(default_config: Config):
    """Test getting balance for a known Solana wallet."""
    client = Web3ClientFactory.get_instance().get_client("solana", default_config)

    # Test wallet with known SOL balance
    # Using a known active Solana wallet (Binance hot wallet)
    wallet = "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E"
    balance = client.get_token_balance("SOL", wallet, "solana")

    assert balance is not None
    assert balance > 0
    print(f"Wallet balance: {balance}")


def test_get_base_balance(default_config: Config):
    """Test getting SOL balance for a known Base wallet."""
    client = Web3ClientFactory.get_instance().get_client("base", default_config)

    # Test wallet with known balance
    # Using a known active Base wallet (Binance hot wallet)
    wallet = "0xF977814e90dA44bFA03b6295A0616a897441aceC"
    token = "USDC"
    balance = client.get_token_balance(token, wallet, "base")

    assert balance is not None
    assert balance > 0
    print(f"Wallet balance: {balance}")


def test_get_eth_balance(default_config: Config):
    """Test getting balance for a known ETH wallet."""
    client = Web3ClientFactory.get_instance().get_client("ethereum", default_config)

    # Test wallet with known balance
    # Using a known active ETH wallet (Binance hot wallet)
    wallet = "0xF977814e90dA44bFA03b6295A0616a897441aceC"
    token = "ETH"
    balance = client.get_token_balance(token, wallet, "ethereum")

    assert balance is not None
    assert balance > 0
    print(f"Wallet balance: {balance}")
