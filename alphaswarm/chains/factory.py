from __future__ import annotations

import logging
from typing import Dict

from alphaswarm.chains.base import Web3Client
from alphaswarm.config import Config

from .evm import SUPPORTED_CHAINS as EVM_CHAINS
from .evm import EVMClient
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

    def __init__(self) -> None:
        # Initialize only once
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._clients = {}

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
        # Return existing client if we have one
        if chain in self._clients:
            return self._clients[chain]

        # Create new client based on chain
        client: Web3Client
        if chain in EVM_CHAINS:
            client = EVMClient(config)
        elif chain in SOLANA_CHAINS:
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
