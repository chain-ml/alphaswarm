import datetime
import logging
from decimal import Decimal
from typing import Any, Optional, Union

from alphaswarm.config import Config, TokenInfo
from eth_account import Account
from eth_defi.confirmation import wait_transactions_to_complete
from eth_defi.token import TokenDetails, fetch_erc20_details
from eth_typing import ChecksumAddress
from hexbytes import HexBytes
from web3 import Web3
from web3.contract import Contract
from web3.contract.contract import ContractFunction
from web3.types import TxParams, TxReceipt, Wei

from .constants_erc20 import ERC20_ABI

logger = logging.getLogger(__name__)

# Define supported chains
SUPPORTED_CHAINS = {"ethereum", "ethereum_sepolia", "base", "base_sepolia"}


class EVMSigner:
    def __init__(self, private_key: str, gas_limit: int = 200_000) -> None:
        self._private_key = private_key
        self._gas_limit = gas_limit
        self._account = Account.from_key(self._private_key)

    def _build_transaction(self, client: Web3, function: ContractFunction) -> TxParams:
        latest_block = client.eth.get_block("latest")
        base_fee = latest_block["baseFeePerGas"]
        priority_fee = client.eth.max_priority_fee
        max_fee_per_gas = client.to_wei(base_fee * 2 + priority_fee, "wei")
        tx: TxParams = function.build_transaction(
            {
                "gas": self._gas_limit,
                "chainId": client.eth.chain_id,
                "from": self._account.address,
                "maxFeePerGas": max_fee_per_gas,
                "maxPriorityFeePerGas": priority_fee,
                "nonce": client.eth.get_transaction_count(client.to_checksum_address(self._account.address)),
            }
        )

        return tx

    def _sign_transaction(self, transaction: TxParams) -> Any:
        return self._account.sign_transaction(transaction)

    def process(self, client: Web3, function: ContractFunction) -> TxReceipt:
        tx = self._build_transaction(client, function)
        signed_tx = self._account.sign_transaction(tx)
        tx_hash = client.eth.send_raw_transaction(signed_tx.rawTransaction)
        return self.wait_for_transaction(client, tx_hash)

    def wait_for_transaction(self, client: Web3, tx_hash: HexBytes) -> TxReceipt:
        result = wait_transactions_to_complete(
            client,
            [tx_hash],
            max_timeout=datetime.timedelta(minutes=2.5),
            # confirmation_block_count=2
        )

        tx_result = result.get(tx_hash, None)
        if tx_result is None:
            raise RuntimeError(f"Transaction {tx_hash!r} not found.")

        return tx_result


class EMVContract:
    def __init__(self, client: Web3, address: ChecksumAddress, abi: list[dict]):
        self._client = client
        self._address = address
        self._abi = abi
        self._contract = client.eth.contract(address=address, abi=abi)

    @property
    def contract(self) -> Contract:
        return self._contract

    @property
    def address(self) -> ChecksumAddress:
        return self._address


class ERC20Contract(EMVContract):
    def __init__(self, client: Web3, address: ChecksumAddress) -> None:
        super().__init__(client, address, ERC20_ABI)
        self._details: Optional[TokenInfo] = None

    @property
    def details(self) -> TokenInfo:
        if self._details is None:
            details = fetch_erc20_details(self._client, self._address)
            self._details = TokenInfo(
                symbol=details.symbol,
                decimals=details.decimals,
                address=details.address,
                chain="changeme",
                is_native=False,
            )
        return self._details

    def get_balance(self, owner: ChecksumAddress) -> Decimal:
        return self.contract.functions.balanceOf(owner).call()

    def get_allowance(self, owner: ChecksumAddress, spender: ChecksumAddress) -> Wei:
        return self.contract.functions.allowance(owner, spender).call()

    def get_allowance_token(self, owner: ChecksumAddress, spender: ChecksumAddress) -> Decimal:
        return self.details.convert_from_wei(self.get_allowance(owner, spender))

    def approve_token(self, spender: ChecksumAddress, value: Decimal) -> ContractFunction:
        return self.approve(spender, self.details.convert_to_wei(value))

    def approve(self, spender: ChecksumAddress, value: Union[Wei, int]) -> ContractFunction:
        return self.contract.functions.approve(spender, value)


class EVMClient:
    """Client for interacting with EVM-compatible chains"""

    def __init__(self, config: Config, chain: str) -> None:
        self._config = config
        self._chain = chain
        self._chain_config = self._config.get_chain_config(chain)
        self._client = Web3(Web3.HTTPProvider(self._chain_config.rpc_url))
        logger.info("Initialized EVMClient")

    @staticmethod
    def _validate_chain(chain: str) -> None:
        """Validate that the chain is supported by EVMClient"""
        if chain not in SUPPORTED_CHAINS:
            raise ValueError(f"Chain '{chain}' is not supported by EVMClient. Supported chains: {SUPPORTED_CHAINS}")

    @classmethod
    def _to_checksum_address(cls, address: str) -> ChecksumAddress:
        """Convert address to checksum format"""
        return Web3.to_checksum_address(address)

    def _get_token_details(self, token_address: str) -> TokenDetails:
        return fetch_erc20_details(self._client, token_address, chain_id=self._client.eth.chain_id)

    def get_token_info(self, token_address: str) -> TokenInfo:
        """Get token info by token contract address"""
        token_details: TokenDetails = self._get_token_details(token_address)
        symbol = token_details.symbol
        decimals = token_details.decimals
        return TokenInfo(symbol=symbol, address=token_address, decimals=decimals, chain=self._chain, is_native=False)

    def get_native_token_balance(self, wallet_address: ChecksumAddress) -> Decimal:
        return Decimal(self._client.eth.get_balance(self._to_checksum_address(wallet_address)))

    def get_token_balance(self, token: str, wallet_address: ChecksumAddress) -> Decimal:
        """Get balance for token symbol (resolved via Config) for a wallet address"""
        if token == "ETH":
            return self.get_native_token_balance(wallet_address)

        token_info = self._chain_config.get_token_info(token)
        token_address = token_info.address
        token_details = self._get_token_details(token_address)
        # TODO this should be using ERC20Contract which would introduce a circular dependency
        return token_details.fetch_balance_of(self._to_checksum_address(wallet_address))
