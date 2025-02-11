from alphaswarm.services.chains import SolanaClient
from alphaswarm.config import Config


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
