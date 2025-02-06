import logging
from decimal import Decimal

from alphaswarm.config import ChainConfig
from solana.rpc import api
from solana.rpc.types import TokenAccountOpts
from solders.pubkey import Pubkey

logger = logging.getLogger(__name__)

# Define supported chains
SUPPORTED_CHAINS = {"solana", "solana_devnet"}


class SolanaClient:
    """Client for interacting with Solana chains"""

    def __init__(self, chain_config: ChainConfig) -> None:
        self._validate_chain(chain_config.chain)
        self._chain_config = chain_config
        self._client = api.Client(self._chain_config.rpc_url)
        logger.info(f"Initialized SolanaClient on chain '{self._chain_config.chain}'")

    @staticmethod
    def _validate_chain(chain: str) -> None:
        """Validate that the chain is supported by SolanaClient"""
        if chain not in SUPPORTED_CHAINS:
            raise ValueError(f"Chain '{chain}' is not supported by SolanaClient. Supported chains: {SUPPORTED_CHAINS}")

    def get_token_balance(self, token: str, wallet_address: str) -> Decimal:
        """Get token balance for a wallet address.

        Args:
            token: Token name (resolved via Config) or 'SOL' for native SOL
            wallet_address: The wallet address to check balance for

        Returns:
            Optional[float]: The token balance in human-readable format, or None if error
        """
        token_info = self._chain_config.get_token_info(token)

        # Handle native SOL balance
        if token.upper() == "SOL":
            pubkey = Pubkey.from_string(wallet_address)
            response = self._client.get_balance(pubkey)
            return Decimal(response.value) / 1_000_000_000

        token_address = token_info.address

        token_pubkey = Pubkey.from_string(token_address)
        wallet_pubkey = Pubkey.from_string(wallet_address)

        # Get token accounts
        opts = TokenAccountOpts(mint=token_pubkey)
        token_accounts = self._client.get_token_accounts_by_owner_json_parsed(wallet_pubkey, opts)

        if not token_accounts.value:
            return Decimal(0)  # No token account found means 0 balance

        # Get balance from account data
        account_data = token_accounts.value[0].account.data.parsed

        # Type checking to prevent issues (and lint errors)
        if not isinstance(account_data, dict):
            raise ValueError("Unexpected data format: 'parsed' is not a dict")

        info = account_data.get("info")
        if not isinstance(info, dict):
            raise ValueError("'info' is not a dict")

        token_amount = info.get("tokenAmount")
        if not isinstance(token_amount, dict):
            raise ValueError("'tokenAmount' is not a dict")

        amount_json = token_amount["amount"]
        if isinstance(amount_json, (str, int, float)):
            balance = Decimal(amount_json)
        elif amount_json is None:
            balance = Decimal(0)  # or handle None how you like
        else:
            raise TypeError(f"Unexpected type for amount: {type(amount_json)}")

        decimals_json = token_amount["decimals"]
        if isinstance(decimals_json, (str, int, float)):
            decimals = Decimal(decimals_json)
        elif amount_json is None:
            decimals = Decimal(0)  # or handle None how you like
        else:
            raise TypeError(f"Unexpected type for decimals: {type(decimals_json)}")

        # Convert to human-readable format
        return balance / 10**decimals
