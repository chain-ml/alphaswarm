from __future__ import annotations

from typing import List, Optional

from alphaswarm.config import WalletInfo
from alphaswarm.core.token import TokenAmount
from alphaswarm.services.chains import SolanaClient
from alphaswarm.services.chains.solana.jupiter_client import JupiterClient
from alphaswarm.services.helius import EnhancedTransaction, HeliusClient, TokenTransfer
from alphaswarm.services.portfolio.portfolio_base import PortfolioBase, PortfolioSwap
from solders.pubkey import Pubkey
from solders.signature import Signature


class PortfolioSolana(PortfolioBase):
    def __init__(
        self,
        wallet: WalletInfo,
        solana_client: SolanaClient,
        helius_client: HeliusClient,
        jupiter_client: JupiterClient,
    ) -> None:
        super().__init__(wallet)
        self._solana_client = solana_client
        self._helius_client = helius_client
        self._jupiter_client = jupiter_client

    def get_token_balances(self) -> List[TokenAmount]:
        return self._solana_client.get_all_token_balances(Pubkey.from_string(self._wallet.address))

    def get_swaps(self) -> List[PortfolioSwap]:
        result = []
        before: Optional[Signature] = None
        page_size = 100
        last_page = page_size
        wallet = Pubkey.from_string(self._wallet.address)

        while last_page >= page_size:
            signatures = self._solana_client.get_signatures_for_address(wallet, page_size, before)
            if len(signatures) == 0:
                break

            last_page = len(signatures)
            before = signatures[-1].signature
            result.extend(self._signatures_to_swaps([str(item.signature) for item in signatures]))
        return result

    def _signatures_to_swaps(self, signatures: List[str]) -> List[PortfolioSwap]:
        result = []
        chunk_size = 100
        for chunk in [signatures[i : i + chunk_size] for i in range(0, len(signatures), chunk_size)]:
            transactions = self._helius_client.get_transactions(chunk)
            for item in transactions:
                swap = self._transaction_to_swap(item)
                if swap is not None:
                    result.append(swap)
        return result

    def _transaction_to_swap(self, transaction: EnhancedTransaction) -> Optional[PortfolioSwap]:
        transfer_out: Optional[TokenTransfer] = next(
            (item for item in transaction.token_transfers if item.from_user_account == self._wallet.address), None
        )
        transfer_in: Optional[TokenTransfer] = next(
            (item for item in transaction.token_transfers if item.to_user_account == self._wallet.address), None
        )

        if transfer_out is None or transfer_in is None:
            return None

        return PortfolioSwap(
            bought=self.transfer_to_token_amount(transfer_in),
            sold=self.transfer_to_token_amount(transfer_out),
            hash=transaction.signature,
            block_number=transaction.slot,
        )

    def transfer_to_token_amount(self, transaction: TokenTransfer) -> TokenAmount:
        token_info = self._solana_client.get_token_info(transaction.mint)
        return TokenAmount(token_info, transaction.token_amount)
