from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Dict, Final, List, Optional

import requests
from alphaswarm.services.api_exception import ApiException
from pydantic import Field, field_validator
from pydantic.dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HistoricalPrice:
    value: Decimal
    timestamp: datetime


@dataclass
class HistoricalPriceBySymbol:
    symbol: str
    data: List[HistoricalPrice]


@dataclass
class HistoricalPriceByAddress:
    address: str
    network: str
    data: List[HistoricalPrice]


@dataclass
class Metadata:
    block_timestamp: Annotated[str, Field(alias="blockTimestamp")]


@dataclass
class RawContract:
    address: str
    value: int
    decimal: int

    @field_validator("value", "decimal", mode="before")
    def convert_hex_to_int(cls, value: str) -> int:
        return int(value, 16)


@dataclass
class Transfer:
    """Represents a token transfer transaction.

    A Transfer object captures details about a single token transfer on the blockchain,
    including the block number, transaction hash, addresses involved, token amount,
    asset type, and timestamp.

    Attributes:
        block_number (int): Block number when transfer occurred
        tx_hash (str): Transaction hash
        from_address (str): Address that sent the tokens
        to_address (str): Address that received the tokens
        value (Decimal): Amount of tokens transferred
        asset (str): Token symbol (e.g. "USDC", "WETH")
        category (str): Token category (e.g. "erc20")
        block_timestamp (Optional[str]): ISO timestamp of block, if available
    """

    block_number: Annotated[int, Field(validation_alias="blockNum", default=0)]
    tx_hash: Annotated[str, Field(validation_alias="hash")]
    from_address: Annotated[str, Field(validation_alias="from")]
    to_address: Annotated[str, Field(validation_alias="to")]
    value: Annotated[Decimal, Field(default=Decimal(0))]
    raw_contract: Annotated[RawContract, Field(alias="rawContract")]
    metadata: Metadata
    asset: str = "UNKNOWN"
    category: str = "UNKNOWN"

    @field_validator("block_number", mode="before")
    def convert_hex_block_number(cls, value: str | int) -> int:
        if isinstance(value, str) and value.startswith("0x"):
            return int(value, 16)
        return int(value)

    @field_validator("value", mode="before")
    def convert_to_decimal(cls, value: str | int | float | Decimal) -> Decimal:
        if value is None:
            return Decimal(0)
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))


@dataclass
class Balance:
    contract_address: Annotated[str, Field(validation_alias="contractAddress")]
    value: Annotated[Decimal, Field(validation_alias="tokenBalance", default=Decimal(0))]
    error: Annotated[Optional[str], Field(default=None)]

    @field_validator("value", mode="before")
    def convert_to_decimal(cls, value: str) -> Decimal:
        balance = int(value, 16)
        return Decimal(balance)


NETWORKS = ["eth-mainnet", "base-mainnet", "solana-mainnet", "eth-sepolia", "base-sepolia", "solana-devnet"]


class AlchemyClient:
    """Alchemy API data source for historical token prices"""

    DEFAULT_BASE_URL: Final[str] = "https://api.g.alchemy.com"
    DEFAULT_NETWORK_URL: Final[str] = "https://{network}.g.alchemy.com/v2/{api_key}"
    ENDPOINT_TOKENS_HISTORICAL: Final[str] = "/prices/v1/{api_key}/tokens/historical"

    def __init__(self, *, api_key: str, base_url: str = DEFAULT_BASE_URL) -> None:
        """Initialize Alchemy data source"""
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {"accept": "application/json", "content-type": "application/json"}

    def _make_request(self, url: str, data: Dict) -> Dict:
        """Make API request to Alchemy with exponential backoff for rate limits."""
        max_retries = 3
        base_delay = 1

        for attempt in range(max_retries + 1):
            try:
                response = requests.post(url, json=data, headers=self.headers)

                if response.status_code != 429:
                    if response.status_code >= 400:
                        raise ApiException(response)
                    return response.json()

                if attempt == max_retries:
                    raise ApiException(response)

                delay = base_delay * (2**attempt)
                time.sleep(delay)

            except Exception:
                if attempt < max_retries:
                    continue

        raise RuntimeError("Max retries exceeded for Alchemy API request")

    def get_historical_prices_by_symbol(
        self, symbol: str, start_time: datetime, end_time: datetime, interval: str
    ) -> HistoricalPriceBySymbol:
        """
        Get historical price data for a token

        Args:
            symbol: Token symbol or contract address
            start_time: Start time for historical data
            end_time: End time for historical data
            interval: Time interval (5m, 1h, 1d)
        """
        start_iso = start_time.astimezone(timezone.utc).isoformat()
        end_iso = end_time.astimezone(timezone.utc).isoformat()

        # Prepare request data
        data = {"symbol": symbol, "startTime": start_iso, "endTime": end_iso, "interval": interval}
        url = f"{self.base_url}{self.ENDPOINT_TOKENS_HISTORICAL.format(api_key=self.api_key)}"
        response = self._make_request(url, data)

        return HistoricalPriceBySymbol(**response)

    def get_historical_prices_by_address(
        self,
        *,
        address: str,
        network: str,
        start_time: datetime,
        end_time: datetime,
        interval: str,
    ) -> HistoricalPriceByAddress:
        """
        Get historical price data for a token

        Args:
            address: Token address (e.g. '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48')
            network: Network identifier (e.g. 'eth-mainnet')
            start_time: Start time for historical data
            end_time: End time for historical data
            interval: Time interval (5m, 1h, 1d)
        """
        # Convert times to ISO format
        start_iso = start_time.astimezone(timezone.utc).isoformat()
        end_iso = end_time.astimezone(timezone.utc).isoformat()

        # Prepare request data
        data = {
            "address": address,
            "network": network,
            "startTime": start_iso,
            "endTime": end_iso,
            "interval": interval,
        }
        url = f"{self.base_url}{self.ENDPOINT_TOKENS_HISTORICAL.format(api_key=self.api_key)}"
        response = self._make_request(url, data)
        return HistoricalPriceByAddress(**response)

    def get_transfers(self, *, wallet: str, chain: str, incoming: bool = False) -> List[Transfer]:
        """Fetch raw ERC20 token transfer data from Alchemy API for a given wallet and chain."""
        address_key = "toAddress" if incoming else "fromAddress"
        payload = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "alchemy_getAssetTransfers",
            "params": [
                {
                    "fromBlock": "0x0",
                    "toBlock": "latest",
                    address_key: wallet,
                    "category": ["erc20"],
                    "order": "asc",
                    "withMetadata": True,
                    "excludeZeroValue": True,
                    "maxCount": "0x3e8",
                }
            ],
        }

        data = self._make_request(url=self.network_url(chain=chain), data=payload)
        # Validation of the response structure
        result = data.get("result")
        if result is None or not isinstance(result, dict):
            raise RuntimeError("Alchemy response JSON does not contain a 'result' object.")

        transfers = result.get("transfers")
        if transfers is None or not isinstance(transfers, list):
            raise RuntimeError("Alchemy response JSON does not contain a 'result.transfers' list.")

        parsed_transfers = [Transfer(**transfer) for transfer in transfers if transfer["asset"] is not None]
        return parsed_transfers

    def get_token_balances(self, *, wallet: str, chain: str) -> List[Balance]:

        payload = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "alchemy_getTokenBalances",
            "params": [wallet],
        }
        data = self._make_request(url=self.network_url(chain=chain), data=payload)
        result = data.get("result")
        if result is None or not isinstance(result, dict):
            raise RuntimeError("Alchemy response JSON does not contain a 'result' object.")
        balances = result.get("tokenBalances")
        if balances is None or not isinstance(balances, list):
            raise RuntimeError("Alchemy response JSON does not contain a 'result.transfers' list.")

        parsed_balances = [Balance(**balance) for balance in balances]
        return parsed_balances

    def network_url(self, chain: str) -> str:
        if chain == "ethereum":
            return self.DEFAULT_NETWORK_URL.format(network="eth-mainnet", api_key=self.api_key)
        elif chain == "ethereum_sepolia":
            return self.DEFAULT_NETWORK_URL.format(network="eth-sepolia", api_key=self.api_key)
        elif chain == "base":
            return self.DEFAULT_NETWORK_URL.format(network="base-mainnet", api_key=self.api_key)
        elif chain == "base_sepolia":
            return self.DEFAULT_NETWORK_URL.format(network="base-sepolia", api_key=self.api_key)
        else:
            raise ValueError(f"Unsupported chain {chain}")

    @staticmethod
    def from_env() -> AlchemyClient:
        api_key = os.getenv("ALCHEMY_API_KEY")
        if not api_key:
            raise RuntimeError("ALCHEMY_API_KEY not found in environment variables")

        return AlchemyClient(api_key=api_key)
