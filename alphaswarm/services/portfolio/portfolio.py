from __future__ import annotations

from abc import abstractmethod
from typing import Iterable, List, Self

from solders.pubkey import Pubkey

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


class Portfolio:
    def __init__(self, portfolios: Iterable[PortfolioBase]) -> None:
        self._portfolios = list(portfolios)

    def get_token_balances(self) -> List[TokenAmount]:
        result = []
        for portfolio in self._portfolios:
            result.extend(portfolio.get_token_balances())

        return result

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
            result.append(TokenAmount(value=token_info.convert_from_wei(balance.value), token_info=token_info))
        return result


class PortfolioSolana(PortfolioBase):
    def __init__(self, wallet: WalletInfo, solana_client: SolanaClient) -> None:
        super().__init__(wallet)
        self._solana_client = solana_client

    def get_token_balances(self) -> List[TokenAmount]:
        return self._solana_client.get_all_token_balances(Pubkey.from_string(self._wallet.address))
