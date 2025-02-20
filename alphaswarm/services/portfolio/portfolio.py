from __future__ import annotations

import logging
from abc import abstractmethod
from dataclasses import dataclass
from typing import Iterable, List, Optional, Self

from solders.pubkey import Pubkey

from ..alchemy.alchemy_client import Transfer
from ...config import Config, WalletInfo
from ...core.token import TokenAmount, TokenInfo
from ..alchemy import AlchemyClient
from ..chains import EVMClient, SolanaClient


logger = logging.getLogger(__name__)

@dataclass
class PortfolioPosition:
    base: TokenAmount
    asset: TokenAmount
    hash: str
    block_number: int

    def to_short_string(self) -> str:
        return f"{self.base.value} {self.base.token_info.symbol} -> {self.asset.value} {self.asset.token_info.symbol} ({self.base.token_info.chain} {self.block_number} {self.hash})"

class PortfolioBase:
    def __init__(self, wallet: WalletInfo) -> None:
        self._wallet = wallet

    @abstractmethod
    def get_token_balances(self) -> List[TokenAmount]:
        pass

    @property
    def chain(self) -> str:
        return self._wallet.chain

class Portfolio:
    def __init__(self, portfolios: Iterable[PortfolioBase]) -> None:
        self._portfolios = list(portfolios)

    def get_token_balances(self, chain: Optional[str] = None) -> List[TokenAmount]:
        result = []
        for portfolio in self._portfolios:
            if chain is None or chain == portfolio.chain:
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

    def get_positions(self) -> List[PortfolioPosition]:
        transfer_in = self._alchemy_client.get_transfers(wallet=self._wallet.address, chain=self._wallet.chain, incoming=True)
        transfer_out = self._alchemy_client.get_transfers(wallet=self._wallet.address, chain=self._wallet.chain, incoming=False)
        map_out = {item.tx_hash: item for item in transfer_out}

        result = []
        for transfer in transfer_in:
            matched_out = map_out.get(transfer.tx_hash)
            if matched_out is None:
                logger.debug(f"Transfer {transfer.tx_hash} has no matching output")
                continue
            result.append(PortfolioPosition(
                asset=self.transfer_to_token_amount(transfer),
                base=self.transfer_to_token_amount(matched_out),
                hash=transfer.tx_hash,
                block_number=transfer.block_number,
            ))

        return result

    def transfer_to_token_amount(self, transfer: Transfer) -> TokenAmount:
        token_info = TokenInfo(
            symbol=transfer.asset,
            address=EVMClient.to_checksum_address(transfer.raw_contract.address),
            decimals=transfer.raw_contract.decimal,
            chain=self._wallet.chain,
        )

        value = transfer.value
        return TokenAmount(value=value, token_info=token_info)



class PortfolioSolana(PortfolioBase):
    def __init__(self, wallet: WalletInfo, solana_client: SolanaClient) -> None:
        super().__init__(wallet)
        self._solana_client = solana_client

    def get_token_balances(self) -> List[TokenAmount]:
        return self._solana_client.get_all_token_balances(Pubkey.from_string(self._wallet.address))
