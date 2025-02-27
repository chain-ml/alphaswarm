from __future__ import annotations

from decimal import Decimal
from typing import List

from alphaswarm.config import WalletInfo
from alphaswarm.core.token import TokenAmount, TokenInfo
from alphaswarm.services.alchemy import AlchemyClient
from alphaswarm.services.alchemy.alchemy_client import Transfer
from alphaswarm.services.chains import EVMClient
from alphaswarm.services.portfolio.portfolio_base import PortfolioBase, PortfolioSwap
from web3.types import Wei


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

    def get_swaps(self) -> List[PortfolioSwap]:
        transfer_in = self._alchemy_client.get_transfers(
            wallet=self._wallet.address, chain=self._wallet.chain, incoming=True
        )
        transfer_out = self._alchemy_client.get_transfers(
            wallet=self._wallet.address, chain=self._wallet.chain, incoming=False
        )
        map_out = {item.tx_hash: item for item in transfer_out}

        result = []
        for transfer in transfer_in:
            matched_out = map_out.get(transfer.tx_hash)
            if matched_out is None:
                continue
            result.append(
                PortfolioSwap(
                    bought=self.transfer_to_token_amount(transfer),
                    sold=self.transfer_to_token_amount(matched_out),
                    hash=transfer.tx_hash,
                    block_number=transfer.block_number,
                )
            )

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

    def get_net_asset_value(self, token_base: TokenInfo) -> TokenAmount:
        value = Decimal(0)
        balances = self.get_token_balances()
        for balance in balances:
            if balance.token_info.address == token_base.address:
                value += balance.value
            else:
                exchange_rate = self._alchemy_client.get_token_quote(
                    token_in=balance.token_info.address, token_out=token_base.address, chain=self._wallet.chain
                )
                value += balance.value * exchange_rate

        return token_base.to_amount(value)
