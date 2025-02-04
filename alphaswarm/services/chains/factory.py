from __future__ import annotations

import logging
from typing import Dict

from alphaswarm.config import Config

from .base import Web3Client
from .evm import SUPPORTED_CHAINS as EVM_CHAINS
from .sol import SUPPORTED_CHAINS as SOLANA_CHAINS
from .sol import SolanaClient

logger = logging.getLogger(__name__)


class Web3ClientFactory:
    """Factory class for creating blockchain clients"""

    _instance = None
    _clients: Dict[str, Web3Client] = {}

    def __new__(cls) -> Web3ClientFactory:
        if cls._instance is None:
            cls._instance = super(Web3ClientFactory, cls).__new__(cls)
        return cls._instance

    def get_client(self, chain: str, config: Config) -> Web3Client:
        """Get a blockchain client for the specified chain.

        Args:
            chain: The chain to get a client for (e.g. 'ethereum', 'solana')
            config: Configuration dictionary

        Returns:
            Web3Client: The appropriate blockchain client for the chain

        Raises:
            ValueError: If the chain is not supported
        """
        client = self._clients.get(chain)
        if client is None:
            # if chain in EVM_CHAINS:
            #     client = EVMClient(config)
            if chain in SOLANA_CHAINS:
                client = SolanaClient(config)
            else:
                supported_chains = EVM_CHAINS.union(SOLANA_CHAINS)
                raise ValueError(f"Chain '{chain}' is not supported. Supported chains: {supported_chains}")

            # Cache and return the client
            self._clients[chain] = client
            logger.info(f"Created new {client.__class__.__name__} for chain {chain}")
        return client

    @classmethod
    def get_instance(cls) -> Web3ClientFactory:
        """Get the singleton instance of the factory"""
        return cls()
