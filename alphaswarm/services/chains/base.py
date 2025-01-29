from abc import ABC, abstractmethod
from typing import Optional

from alphaswarm.config import Config, TokenInfo
from eth_typing import ChecksumAddress


class Web3Client(ABC):
    """Abstract base class for blockchain clients"""

    def __init__(self, config: Config) -> None:
        self.config = config

    @abstractmethod
    def to_checksum_address(self, address: str, chain: str) -> ChecksumAddress:
        """Convert address to checksum format"""
        pass

    @abstractmethod
    def get_token_info(self, token_address: str, chain: str) -> TokenInfo:
        """Get token info by token contract address"""
        pass

    @abstractmethod
    def get_token_balance(self, token: str, wallet_address: str, chain: str) -> Optional[float]:
        """Get balance for a token symbol (resolved via Config) for a wallet address"""
        pass
