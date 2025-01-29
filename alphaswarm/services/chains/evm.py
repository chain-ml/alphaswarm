import logging
import os
from decimal import Decimal
from typing import Any, Dict

from alphaswarm.config import Config, TokenInfo
from eth_defi.token import TokenDetails, fetch_erc20_details
from eth_typing import ChecksumAddress
from web3 import Web3
from web3.contract import Contract

from .base import Web3Client

logger = logging.getLogger(__name__)

# Define supported chains
SUPPORTED_CHAINS = {"ethereum", "ethereum_sepolia", "base"}


class EVMClient(Web3Client):
    """Client for interacting with EVM-compatible chains"""

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self._web3_instances: Dict[str, Web3] = {}  # Initialize dict to store web3 instances per chain
        logger.info("Initialized EVMClient")

    @staticmethod
    def _validate_chain(chain: str) -> None:
        """Validate that the chain is supported by EVMClient"""
        if chain not in SUPPORTED_CHAINS:
            raise ValueError(f"Chain '{chain}' is not supported by EVMClient. Supported chains: {SUPPORTED_CHAINS}")

    def get_web3(self, chain: str) -> Web3:
        """Get or create Web3 instance for chain"""
        self._validate_chain(chain)
        if chain not in self._web3_instances:
            # Debug log the config structure
            logger.debug(f"Config structure for web3: {self.config}")

            # Get provider URL from chain config
            rpc_url = None
            chain_config = self.config.get_chain_config(chain)
            if hasattr(chain_config, "rpc_url"):
                rpc_url = chain_config.rpc_url
                if isinstance(rpc_url, dict) and "fromEnvVar" in rpc_url:
                    rpc_url = os.getenv(rpc_url["fromEnvVar"])

            if not rpc_url:
                raise ValueError(f"Could not find RPC URL for chain {chain}")

            self._web3_instances[chain] = Web3(Web3.HTTPProvider(rpc_url))
        return self._web3_instances[chain]

    def get_contract(self, address: str, abi: Any, chain: str) -> Contract:
        """Get contract instance"""
        self._validate_chain(chain)
        web3 = self.get_web3(chain)
        return web3.eth.contract(address=self.to_checksum_address(address, chain), abi=abi)

    @classmethod
    def _to_checksum_address(cls, address: str) -> ChecksumAddress:
        """Convert address to checksum format"""
        return Web3.to_checksum_address(address)

    def to_checksum_address(self, address: str, chain: str) -> ChecksumAddress:
        self._validate_chain(chain)
        return self._to_checksum_address(address)

    def _get_token_details(self, token_address: str, chain: str) -> TokenDetails:
        self._validate_chain(chain)
        web3 = self.get_web3(chain)
        return fetch_erc20_details(web3, token_address, chain_id=web3.eth.chain_id)

    def get_token_info(self, token_address: str, chain: str) -> TokenInfo:
        """Get token info by token contract address"""
        self._validate_chain(chain)
        token_details: TokenDetails = self._get_token_details(token_address, chain)
        symbol = token_details.symbol
        decimals = token_details.decimals
        return TokenInfo(symbol=symbol, address=token_address, decimals=decimals, chain=chain, is_native=False)

    def get_token_balance(self, token: str, wallet_address: str, chain: str) -> Decimal:
        """Get balance for token symbol (resolved via Config) for a wallet address"""
        self._validate_chain(chain)
        if token == "ETH":
            return Decimal(self.get_web3(chain).eth.get_balance(self.to_checksum_address(wallet_address, chain)))

        chain_config = self.config.get_chain_config(chain)
        token_info = chain_config.get_token_info(token)

        token_address = token_info.address
        token_details: TokenDetails = self._get_token_details(token_address, chain)
        return token_details.fetch_balance_of(self.to_checksum_address(wallet_address, chain))
