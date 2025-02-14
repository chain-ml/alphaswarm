import logging
import time
from decimal import Decimal
from typing import Any, Dict

from alphaswarm.config import ChainConfig
from solana.rpc import api
from solana.rpc.types import TokenAccountOpts
from solders.keypair import Keypair
from solders.message import to_bytes_versioned
from solders.pubkey import Pubkey
from solders.rpc.responses import SendTransactionResp
from solders.signature import Signature
from solders.transaction import VersionedTransaction

logger = logging.getLogger(__name__)

# Define supported chains
SUPPORTED_CHAINS = {"solana", "solana_devnet"}


class SolSigner:
    def __init__(self, private_key: str):
        self._keypair = Keypair.from_base58_string(private_key)

    @property
    def wallet_address(self) -> str:
        return str(self._keypair.pubkey())

    def sign(self, message: VersionedTransaction) -> Signature:
        return self._keypair.sign_message(to_bytes_versioned(message.message))


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

        balance = self._get_decimal(token_amount, "amount")
        decimals = self._get_decimal(token_amount, "decimals")

        # Convert to human-readable format
        return balance / 10**decimals

    def process(self, transaction: VersionedTransaction, signer: SolSigner) -> Signature:
        signature = signer.sign(transaction)
        signed_tx = VersionedTransaction.populate(transaction.message, [signature])
        tx_response = self._send_transaction(signed_tx)
        self._wait_for_confirmation(tx_response.value)
        return tx_response.value

    def _send_transaction(self, signed_tx: VersionedTransaction) -> SendTransactionResp:
        try:
            return self._client.send_transaction(signed_tx)
        except Exception as e:
            raise RuntimeError("Failed to send transaction. Make sure you have enough token balance.") from e

    def _wait_for_confirmation(self, signature: Signature) -> None:
        timeout_sec = 10
        sleep_sec = 1

        while timeout_sec > 0:
            tx_status = self._client.get_signature_statuses([signature])
            response = tx_status.value[0]
            if response is not None:
                status = response.confirmation_status
                if status is not None and status.Finalized:
                    return
            time.sleep(sleep_sec)
        raise RuntimeError(f"Failed to get confirmation for transaction '{str(signature)}'")

    @staticmethod
    def _get_decimal(values: Dict[str, Any], key: str) -> Decimal:
        """Helper function to convert JSON value to Decimal"""
        value = values.get(key, Decimal(0))
        if isinstance(value, (str, int)):
            return Decimal(value)
        elif isinstance(value, float):
            return Decimal(str(value))
        else:
            raise TypeError(f"Unexpected type for value {key} : {type(value)}")
