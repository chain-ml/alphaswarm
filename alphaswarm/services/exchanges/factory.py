import logging
from typing import Dict, Type

from alphaswarm.config import Config

from .base import DEXClient
from .jupiter.jupiter import JupiterClient
from .uniswap import UniswapClientV2, UniswapClientV3

logger = logging.getLogger(__name__)


class DEXFactory:
    """Factory for creating DEX client instances"""

    _dex_registry: Dict[str, Type[DEXClient]] = {
        "uniswap_v2": UniswapClientV2,
        "uniswap_v3": UniswapClientV3,
        "jupiter": JupiterClient,
        # Add more DEXes here as they're implemented
    }

    @classmethod
    def create(cls, dex_name: str, config: Config, chain: str) -> DEXClient:
        """Create a DEX client instance"""
        logger.debug(f"Creating DEX client for: {dex_name}")

        dex_client_class = cls._dex_registry.get(dex_name)
        if dex_client_class is None:
            logger.error(f"Unsupported DEX: {dex_name}")
            raise ValueError(f"Unsupported DEX: {dex_name}")

        logger.debug(f"Using DEX class: {dex_client_class.__name__}")
        client = dex_client_class.from_config(config, chain)

        logger.debug("DEX client created successfully")
        return client

    @classmethod
    def register_dex(cls, name: str, dex_class: Type[DEXClient]) -> None:
        """Register a new DEX client class"""
        logger.debug(f"Registering new DEX type: {name} with class {dex_class.__name__}")
        cls._dex_registry[name] = dex_class
