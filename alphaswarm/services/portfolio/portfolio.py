from __future__ import annotations

from abc import abstractmethod
from datetime import UTC, datetime
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Self

from solders.pubkey import Pubkey
from web3.types import Wei

from ...config import Config, WalletInfo
from ...core.token import TokenAmount
from ..alchemy import AlchemyClient
from ..chains import EVMClient, SolanaClient


class PortfolioBase:
    def __init__(self, wallet: WalletInfo) -> None:
        self._wallet = wallet

    @abstractmethod
    def get_token_balances(self) -> List[TokenAmount]:
        pass

    @property
    def chain(self) -> str:
        return self._wallet.chain


class PortfolioBalance:
    def __init__(self, balances: List[TokenAmount]) -> None:
        self._balance_map: Dict[str, TokenAmount] = {balance.token_info.address: balance for balance in balances}
        self._timestamp: datetime = datetime.now(UTC)

    @property
    def timestamp(self) -> datetime:
        """Get UTC timestamp when this balance was captured."""
        return self._timestamp

    def age_seconds(self) -> float:
        """Get age of this balance in seconds."""
        return (datetime.now(UTC) - self._timestamp).total_seconds()

    def has_token(self, token_address: str) -> bool:
        """Check if portfolio has any balance of the given token."""
        return token_address in self._balance_map

    def get_token_balance(self, token_address: str) -> Optional[TokenAmount]:
        """Get balance of specific token, returns None if token not found."""
        return self._balance_map.get(token_address)

    def get_balance_value(self, token_address: str) -> Decimal:
        """Get numerical balance value of token, returns 0 if token not found."""
        balance = self.get_token_balance(token_address)
        return balance.value if balance else Decimal("0")

    def get_all_balances(self) -> List[TokenAmount]:
        """Get list of all token balances."""
        return list(self._balance_map.values())

    def get_non_zero_balances(self) -> List[TokenAmount]:
        """Get list of token balances with non-zero amounts."""
        return [balance for balance in self._balance_map.values() if balance.value > 0]

    @property
    def total_tokens(self) -> int:
        """Get total number of tokens in portfolio."""
        return len(self._balance_map)

    @property
    def non_zero_tokens(self) -> int:
        """Get number of tokens with non-zero balance."""
        return len(self.get_non_zero_balances())

    def has_enough_balance_of(self, amount: TokenAmount) -> bool:
        """
        Check if portfolio has enough balance to spend the given token amount.

        Args:
            amount: TokenAmount to check if sufficient balance exists

        Returns:
            bool: True if portfolio has sufficient balance, False otherwise
        """
        current_balance = self.get_token_balance(amount.token_info.address)
        if current_balance is None:
            return False
        return current_balance >= amount


class Portfolio:
    def __init__(self, portfolios: Iterable[PortfolioBase]) -> None:
        self._portfolios = list(portfolios)

    def get_token_balances(self, chain: Optional[str] = None) -> PortfolioBalance:
        result = []
        for portfolio in self._portfolios:
            if chain is None or chain == portfolio.chain:
                result.extend(portfolio.get_token_balances())

        return PortfolioBalance(result)

    @classmethod
    def from_config(cls, config: Config) -> Self:
        portfolios: List[PortfolioBase] = []
        for chain in config.get_supported_networks():
            chain_config = config.get_chain_config(chain)
            wallet_info = WalletInfo.from_chain_config(chain_config)
            if chain == "solana":
                portfolios.append(PortfolioSolana(wallet_info, SolanaClient(chain_config)))
            if chain in ["ethereum", "ethereum_sepolia", "base"]:
                portfolios.append(PortfolioEvm(wallet_info, EVMClient(chain_config), AlchemyClient.from_env()))
        return cls(portfolios)


class PortfolioEvm(PortfolioBase):
    def __init__(self, wallet: WalletInfo, evm_client: EVMClient, alchemy_client: AlchemyClient) -> None:
        super().__init__(wallet)
        self._evm_client = evm_client
        self._alchemy_client = alchemy_client

    def get_token_balances(self) -> List[TokenAmount]:
        balances = self._alchemy_client.get_token_balances(wallet=self._wallet.address, chain=self._wallet.chain)
        result = []
        for balance in balances:
            token_info = self._evm_client.get_token_info(EVMClient.to_checksum_address(balance.contract_address))
            result.append(token_info.to_amount_from_base_units(Wei(balance.value)))
        return result


class PortfolioSolana(PortfolioBase):
    def __init__(self, wallet: WalletInfo, solana_client: SolanaClient) -> None:
        super().__init__(wallet)
        self._solana_client = solana_client

    def get_token_balances(self) -> List[TokenAmount]:
        return self._solana_client.get_all_token_balances(Pubkey.from_string(self._wallet.address))
