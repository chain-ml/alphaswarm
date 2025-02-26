import logging
import time
from decimal import Decimal
from typing import Annotated, List, Optional, Self

from alphaswarm.config import ChainConfig, TokenInfo
from alphaswarm.core.token import BaseUnit, TokenAmount
from alphaswarm.services.chains.solana.jupiter_client import JupiterClient
from pydantic import BaseModel, Field
from solana.rpc import api
from solana.rpc.commitment import Finalized
from solana.rpc.types import TokenAccountOpts
from solders.account_decoder import ParsedAccount
from solders.keypair import Keypair
from solders.message import to_bytes_versioned
from solders.pubkey import Pubkey
from solders.rpc.responses import RpcConfirmedTransactionStatusWithSignature, SendTransactionResp
from solders.signature import Signature
from solders.transaction import VersionedTransaction
from solders.transaction_status import TransactionConfirmationStatus
from spl.token.constants import TOKEN_PROGRAM_ID

logger = logging.getLogger(__name__)

# Define supported chains
SUPPORTED_CHAINS = {"solana", "solana_devnet"}


class SolanaTokenAmount(BaseModel):
    decimals: int
    amount: int


class AccountInfo(BaseModel):
    is_native: Annotated[bool, Field(alias="isNative")]
    mint: str
    owner: str
    state: str
    token_amount: Annotated[SolanaTokenAmount, Field(alias="tokenAmount")]

    @classmethod
    def from_parsed_account(cls, parse_account: ParsedAccount) -> Self:
        if parse_account.parsed.get("type") != "account":
            raise ValueError("Account type must be 'account'")
        info = parse_account.parsed["info"]
        return cls.model_validate(info)


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

    def get_token_info(self, token_address: str) -> TokenInfo:
        result = self._chain_config.get_token_info_by_address_or_none(token_address)
        if result is not None:
            return result

        client = JupiterClient()
        return client.get_token_info(token_address).to_token_info()

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
        account_data = token_accounts.value[0].account.data
        account_info = AccountInfo.from_parsed_account(account_data)

        # Convert to human-readable format
        return account_info.token_amount.amount / 10**account_info.token_amount.decimals

    def get_all_token_balances(self, public_key: Pubkey) -> List[TokenAmount]:
        response = self._client.get_token_accounts_by_owner_json_parsed(
            public_key, TokenAccountOpts(program_id=TOKEN_PROGRAM_ID)
        )
        result = []
        for account in response.value:
            value = AccountInfo.from_parsed_account(account.account.data)
            if value.token_amount.amount == 0:
                continue
            token_info = self.get_token_info(value.mint)
            token_amount = token_info.to_amount_from_base_units(BaseUnit(value.token_amount.amount))
            result.append(token_amount)
        return result

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
        initial_timeout = 30
        timeout_sec = initial_timeout
        sleep_sec = 2
        status: Optional[TransactionConfirmationStatus] = None
        while timeout_sec > 0:
            tx_status = self._client.get_signature_statuses([signature])
            response = tx_status.value[0]
            if response is not None:
                status = response.confirmation_status
                if status is not None and status.Finalized:
                    return
            logger.warning(f"Status {status} for transaction {str(signature)}. Retrying in {sleep_sec} seconds...")
            time.sleep(sleep_sec)
            timeout_sec -= sleep_sec
        raise RuntimeError(
            f"Failed to get confirmation for transaction '{str(signature)}' for {initial_timeout} seconds. Last status is {status}"
        )

    def get_signatures_for_address(
        self, wallet_address: Pubkey, limit: int = 1000, before: Optional[Signature] = None
    ) -> List[RpcConfirmedTransactionStatusWithSignature]:

        result = self._client.get_signatures_for_address(
            wallet_address, commitment=Finalized, limit=limit, before=before
        )
        return result.value
