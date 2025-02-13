from __future__ import annotations

import logging
import os
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

import yaml
from alphaswarm import BASE_PATH
from eth_typing import ChecksumAddress
from pydantic.dataclasses import dataclass
from web3 import Web3

logger = logging.getLogger(__name__)

NATIVE_TOKENS = {"ethereum": ["ETH"], "ethereum_sepolia": ["ETH"], "base": ["ETH"], "solana": ["SOL"]}


CONFIG_PATH = BASE_PATH / "config"


@dataclass
class TokenInfo:
    symbol: str
    address: str
    decimals: int
    chain: str
    is_native: bool = False

    def convert_to_wei(self, amount: Decimal) -> int:
        return int(amount * (10**self.decimals))

    def convert_from_wei(self, amount: Union[int, Decimal]) -> Decimal:
        return Decimal(amount) / (10**self.decimals)

    def address_to_path(self) -> str:
        # Remove '0x' and pad to 20 bytes
        return self.address.removeprefix("0x").zfill(40)

    @property
    def checksum_address(self) -> ChecksumAddress:
        """Get the checksum address for this token"""
        return Web3.to_checksum_address(self.address)


@dataclass
class GasSettings:
    max_priority_fee: int
    gas_limit: int


@dataclass
class ChainConfig:
    chain: str
    wallet_address: str
    private_key: str
    rpc_url: str
    tokens: Dict[str, TokenInfo]
    gas_settings: Optional[GasSettings] = None

    def get_token_info(self, symbol: str) -> TokenInfo:
        """Get token info for a symbol"""
        if symbol not in self.tokens:
            raise ValueError(f"Token {symbol} not found in chain config for {self.chain}")
        return self.tokens[symbol]

    def get_token_info_or_none(self, symbol: str) -> Optional[TokenInfo]:
        """Get token info for a symbol, returning None if not found"""
        if symbol not in self.tokens:
            return None
        return self.tokens[symbol]

    def get_token_info_by_address(self, address: str) -> TokenInfo:
        """Get token info for an address, raise ValueError if not found"""
        result = self.get_token_info_by_address_or_none(address)
        if result is None:
            raise ValueError(f"Token {address} not found in chain config for {self.chain}")
        return result

    def get_token_info_by_address_or_none(self, address: str) -> Optional[TokenInfo]:
        """Get token info from its address, returning None if not found"""
        return next((token for token in self.tokens.values() if token.address == address), None)


@dataclass
class UniswapV2Venue:
    supported_pairs: List[str]


@dataclass
class UniswapV3Venue:
    supported_pairs: List[str]


@dataclass
class UniswapV3Settings:
    fee_tiers: List[int]


@dataclass
class JupiterVenue:
    quote_api_url: str
    swap_api_url: str
    supported_pairs: List[str]


@dataclass
class JupiterSettings:
    slippage_bps: int


class Config:
    _instance = None

    @staticmethod
    def configure_logging() -> None:
        """Configure logging for the entire application"""
        # Get log level from environment, strip any comments and whitespace
        log_level = os.getenv("LOG_LEVEL", "INFO").split("#")[0].strip().upper()

        # Get log format from environment, with a default that includes line numbers
        log_format = os.getenv(
            "LOG_FORMAT", "%(asctime)s - %(name)s:%(lineno)d - %(funcName)s - %(levelname)s - %(message)s"
        )

        # Validate log level
        valid_levels = logging.getLevelNamesMapping().keys()
        if log_level not in valid_levels:
            log_level = "INFO"

        logging.basicConfig(
            level=getattr(logging, log_level),
            format=log_format,
            force=True,  # Ensure our configuration takes precedence
        )
        logger.debug(f"Logging configured with level {log_level} and format {log_format}")

    def __init__(self, *, config_path: Optional[str] = None, network_env: str = "production") -> None:
        """Initialize configuration with optional network environment filter.

        Args:
            network_env (str): Network environment to use. One of: "production", "test", "all"
        """
        self._network_env = network_env
        self._load_config(config_path)

    @staticmethod
    def _substitute_env_vars(value: Any) -> Any:
        """Replace environment variable references with their values"""
        if isinstance(value, dict) and "fromEnvVar" in value:
            env_var = value["fromEnvVar"]
            env_value = os.getenv(env_var, "")
            if not env_value:
                raise ValueError(f"Environment variable {env_var} not found")
            return env_value
        return value

    def _resolve_config_reference(self, value: Any) -> Any:
        """Resolve references to other parts of the config using ${...} syntax"""
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            ref_path = value[2:-1]
            try:
                keys = ref_path.split(".")
                result = self._config
                for key in keys:
                    result = result[key]
                return result
            except (KeyError, TypeError):
                logger.warning(f"Could not resolve config reference: {ref_path}")
                return value
        return value

    def _process_config(self, config: Dict, process_env_vars: bool = True) -> Dict:
        """Recursively process config and substitute environment variables and references"""
        if not isinstance(config, dict):
            return config

        processed: Dict = {}
        for key, value in config.items():
            # First handle environment variables if enabled
            if process_env_vars:
                value = self._substitute_env_vars(value)

            # Then process nested structures
            if isinstance(value, dict):
                processed[key] = self._process_config(value, process_env_vars)
            elif isinstance(value, list):
                processed[key] = [
                    self._process_config(item, process_env_vars) if isinstance(item, dict) else item for item in value
                ]
            else:
                # Only try to resolve config references if we're not processing env vars
                if not process_env_vars and isinstance(value, str):
                    value = self._resolve_config_reference(value)
                processed[key] = value

        return processed

    def _load_config(self, config_path: Optional[str] = None) -> None:
        """Load configuration from YAML and substitute environment variables"""
        actual_path = config_path or str(CONFIG_PATH / "default.yaml")
        logger.info(f"Loading configuration from '{actual_path}'")

        with open(actual_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f)

        # First pass: process only environment variables
        self._config = self._process_config(self._config, process_env_vars=True)

        # Second pass: resolve config references
        self._config = self._process_config(self._config, process_env_vars=False)

        # Filter networks based on environment
        if self._network_env != "all":
            self._filter_networks()

    def _filter_networks(self) -> None:
        """Filter trading venues based on network environment"""
        allowed_networks = self._config["network_environments"].get(self._network_env, [])

        # Filter trading venues
        for venue_type in list(self._config["trading_venues"].keys()):
            filtered_venue = {}
            for network, config in self._config["trading_venues"][venue_type].items():
                if network == "settings" or network in allowed_networks:
                    filtered_venue[network] = config
            self._config["trading_venues"][venue_type] = filtered_venue

        # Filter chain_config based on allowed networks
        filtered_chain_config = {}
        for network, config in self._config["chain_config"].items():
            if network in allowed_networks:
                filtered_chain_config[network] = config
        self._config["chain_config"] = filtered_chain_config

    def get_supported_networks(self) -> list:
        """Get list of supported networks for current environment"""
        return self._config["network_environments"].get(self._network_env, [])

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value using dot notation"""
        try:
            keys = key_path.split(".")
            value = self._config
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def get_chain_config(self, chain: str) -> ChainConfig:
        chain_config_dict: Dict[str, Any] = self._config["chain_config"]
        if chain not in chain_config_dict:
            raise ValueError(f"Unknown chain! Configured chains: {', '.join(chain_config_dict.keys())}")

        values = chain_config_dict[chain].copy()
        values["chain"] = chain
        # Convert each token config into a TokenInfo instance
        if "tokens" in values:
            values["tokens"] = {
                symbol: TokenInfo(symbol=symbol, chain=chain, **token_config)
                for symbol, token_config in values["tokens"].items()
            }
        return ChainConfig(**values)

    def get_chain_config_or_none(self, chain: str) -> Optional[ChainConfig]:
        """Get chain config or None if chain doesn't exist"""
        try:
            return self.get_chain_config(chain)
        except KeyError:
            return None

    def get_trading_venues(self) -> Dict[str, Any]:
        """Get all trading venues configuration"""
        return self._config.get("trading_venues", {})

    def get_trading_venues_for_chain(self, chain: str) -> List[str]:
        """Get all trading venues configuration for a chain"""
        result = []
        for name, value in self.get_trading_venues().items():
            if isinstance(value, dict) and value.get(chain) is not None:
                result.append(name)

        return result

    def get_venue_uniswap_v2(self, chain: str) -> UniswapV2Venue:
        values = self._config["trading_venues"]["uniswap_v2"][chain]
        return UniswapV2Venue(**values)

    def get_venue_uniswap_v3(self, chain: str) -> UniswapV3Venue:
        values = self._config["trading_venues"]["uniswap_v3"][chain]
        return UniswapV3Venue(**values)

    def get_venue_settings_uniswap_v3(self) -> UniswapV3Settings:
        values = self._config["trading_venues"]["uniswap_v3"]["settings"]
        return UniswapV3Settings(**values)

    def get_venue_jupiter(self, chain: str) -> JupiterVenue:
        values = self._config["trading_venues"]["jupiter"][chain]
        return JupiterVenue(**values)

    def get_venue_settings_jupiter(self) -> JupiterSettings:
        values = self._config["trading_venues"]["jupiter"]["settings"]
        return JupiterSettings(**values)
