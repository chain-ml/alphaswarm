import logging
from decimal import Decimal
from typing import List

from alphaswarm.config import ChainConfig, TokenInfo
from eth_account import Account
from eth_account.datastructures import SignedTransaction
from eth_defi.token import TokenDetails, fetch_erc20_details
from eth_typing import ChecksumAddress
from hexbytes import HexBytes
from web3 import Web3
from web3.contract import Contract
from web3.contract.contract import ContractFunction
from web3.types import TxParams, TxReceipt, Wei

logger = logging.getLogger(__name__)

# Define supported chains
SUPPORTED_CHAINS = {"ethereum", "ethereum_sepolia", "base", "base_sepolia"}
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
ZERO_CHECKSUM_ADDRESS = Web3.to_checksum_address(ZERO_ADDRESS)
DEFAULT_GAS_LIMIT = 200_000  # Default gas limit for transactions


class EVMSigner:
    def __init__(self, private_key: str) -> None:
        self._account = Account.from_key(private_key)

    @property
    def address(self) -> ChecksumAddress:
        return self._account.address

    def sign_transaction(self, transaction: TxParams) -> SignedTransaction:
        return self._account.sign_transaction(transaction)


class EVMClient:
    """Client for interacting with EVM-compatible chains"""

    def __init__(self, chain_config: ChainConfig) -> None:
        self._validate_chain(chain_config.chain)
        self._chain_config = chain_config
        self._client = Web3(Web3.HTTPProvider(self._chain_config.rpc_url))
        self._gas_limit = (
            self._chain_config.gas_settings.gas_limit if self._chain_config.gas_settings else DEFAULT_GAS_LIMIT
        )
        logger.info(f"Initialized EVMClient on chain {self._chain_config.chain}")

    @property
    def chain(self) -> str:
        return self._chain_config.chain

    @property
    def client(self) -> Web3:
        return self._client

    @staticmethod
    def _validate_chain(chain: str) -> None:
        """Validate that the chain is supported by EVMClient"""
        if chain not in SUPPORTED_CHAINS:
            raise ValueError(f"Chain '{chain}' is not supported by EVMClient. Supported chains: {SUPPORTED_CHAINS}")

    @classmethod
    def to_checksum_address(cls, address: str) -> ChecksumAddress:
        """Convert address to checksum format"""
        return Web3.to_checksum_address(address)

    def get_token_details(self, token_address: ChecksumAddress) -> TokenDetails:
        return fetch_erc20_details(self._client, token_address, chain_id=self._client.eth.chain_id)

    def get_token_info(self, token_address: ChecksumAddress) -> TokenInfo:
        """Get token info by token contract address"""
        token_details: TokenDetails = self.get_token_details(token_address)
        symbol = token_details.symbol
        decimals = token_details.decimals
        return TokenInfo(symbol=symbol, address=token_address, decimals=decimals, chain=self.chain, is_native=False)

    def get_token_info_by_name(self, name: str) -> TokenInfo:
        return self._chain_config.get_token_info(name)

    def get_native_balance(self, wallet_address: ChecksumAddress) -> Wei:
        return Wei(self._client.eth.get_balance(self.to_checksum_address(wallet_address)))

    def get_token_balance(self, token: str, wallet_address: ChecksumAddress) -> Decimal:
        """Get balance for token symbol (resolved via Config) for a wallet address"""
        token_info = self.get_token_info_by_name(token)
        if token_info.is_native:
            return token_info.convert_from_wei(self.get_native_balance(wallet_address))

        token_details = self.get_token_details(token_info.checksum_address)
        # TODO this should be using ERC20Contract which would introduce a circular dependency
        return token_details.fetch_balance_of(self.to_checksum_address(wallet_address))

    def process(self, function: ContractFunction, signer: EVMSigner) -> TxReceipt:
        tx = self._build_transaction(function, signer.address)
        signed_tx = signer.sign_transaction(tx)
        tx_hash = self._client.eth.send_raw_transaction(signed_tx.rawTransaction)
        result: TxReceipt = self.wait_for_transaction(tx_hash)

        # TODO
        # if result["status"] == 0:
        #     reason = fetch_transaction_revert_reason(self._client, tx_hash)
        #     logger.error(f"Transaction {tx_hash.hex()} failed because of: {reason}")
        return result

    def get_contract(self, address: ChecksumAddress, abi: List[dict]) -> Contract:
        return self._client.eth.contract(address=address, abi=abi)

    def _build_transaction(self, function: ContractFunction, wallet_address: ChecksumAddress) -> TxParams:
        latest_block = self._client.eth.get_block("latest")
        base_fee = latest_block["baseFeePerGas"]
        priority_fee = self._client.eth.max_priority_fee
        max_fee_per_gas = self._client.to_wei(base_fee * 2 + priority_fee, "wei")
        tx: TxParams = function.build_transaction(
            {
                "gas": self._gas_limit,
                "chainId": self._client.eth.chain_id,
                "from": wallet_address,
                "maxFeePerGas": max_fee_per_gas,
                "maxPriorityFeePerGas": priority_fee,
                "nonce": self._client.eth.get_transaction_count(wallet_address),
            }
        )

        return tx

    def wait_for_transaction(self, tx_hash: HexBytes, timeout: int = 120, poll_latency: float = 1) -> TxReceipt:
        return self._client.eth.wait_for_transaction_receipt(tx_hash, timeout, poll_latency)
