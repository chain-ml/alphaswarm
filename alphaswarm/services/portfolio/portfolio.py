from __future__ import annotations

import logging
from abc import abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum, auto
from typing import Callable, Dict, Iterable, List, Optional, Self, Sequence

from solders.pubkey import Pubkey
from solders.signature import Signature
from web3.types import Wei

from ...config import ChainConfig, Config, WalletInfo
from ...core.token import TokenAmount, TokenInfo
from ..alchemy import AlchemyClient
from ..alchemy.alchemy_client import Transfer
from ..chains import EVMClient, SolanaClient
from ..chains.solana.jupiter_client import JupiterClient
from ..helius import EnhancedTransaction, HeliusClient, TokenTransfer

logger = logging.getLogger(__name__)


class PnlMode(Enum):
    TOTAL = auto()
    REALIZED = auto()
    UNREALIZED = auto()


class PortfolioPNL:
    def __init__(self) -> None:
        self._details_per_asset: Dict[str, List[PortfolioPNLDetail]] = {}

    def add_details(self, asset: str, details: Iterable[PortfolioPNLDetail]) -> None:
        self._details_per_asset[asset] = list(details)

    def pnl_per_asset(self, mode: PnlMode = PnlMode.TOTAL) -> Dict[str, Decimal]:
        result = {}
        for asset, details in self._details_per_asset.items():
            result[asset] = sum([item.pnl for item in details if item.is_in_scope(mode)], Decimal(0))
        return result

    def pnl(self, mode: PnlMode = PnlMode.TOTAL) -> Decimal:
        return sum([pnl for asset, pnl in self.pnl_per_asset(mode).items()], Decimal(0))


class PortfolioPNLDetail:
    def __init__(self, bought: PortfolioSwap, selling_price: Decimal, sold_amount: Decimal, is_realized: bool) -> None:
        self._bought = bought
        self._selling_price = selling_price
        self._sold_amount = sold_amount
        self._is_realized = is_realized
        self._pnl = sold_amount * (self._selling_price - self.buying_price)

    @property
    def buying_price(self) -> Decimal:
        """Buying price per asset"""
        return self._bought.sold.value / self._bought.bought.value

    @property
    def sold_amount(self) -> Decimal:
        return self._sold_amount

    @property
    def selling_price(self) -> Decimal:
        return self._selling_price

    @property
    def pnl(self) -> Decimal:
        return self._pnl

    @property
    def is_realized(self) -> bool:
        return self._is_realized

    def is_in_scope(self, mode: PnlMode) -> bool:
        return (
            mode == PnlMode.TOTAL
            or (mode == PnlMode.REALIZED and self._is_realized)
            or (mode == PnlMode.UNREALIZED and not self._is_realized)
        )


class PortfolioRealizedPNLDetail(PortfolioPNLDetail):
    def __init__(self, bought: PortfolioSwap, sold: PortfolioSwap, sold_amount: Decimal) -> None:
        if bought.block_number > sold.block_number:
            raise ValueError("bought block number is greater than sold block number")

        super().__init__(bought, sold.bought.value / sold.sold.value, sold_amount, is_realized=True)
        self._sold = sold


class PortfolioUnrealizedPNLDetail(PortfolioPNLDetail):
    def __init__(self, bought: PortfolioSwap, selling_price: Decimal, sold_amount: Decimal) -> None:
        super().__init__(bought, selling_price, sold_amount, is_realized=False)


@dataclass
class PortfolioSwap:
    sold: TokenAmount
    bought: TokenAmount
    hash: str
    block_number: int

    def to_short_string(self) -> str:
        return f"{self.sold.value} {self.sold.token_info.symbol} -> {self.bought.value} {self.bought.token_info.symbol} ({self.sold.token_info.chain} {self.block_number} {self.hash})"


PricingFunction = Callable[[str, str], Decimal]


class PortfolioBase:
    def __init__(self, wallet: WalletInfo) -> None:
        self._wallet = wallet

    @abstractmethod
    def get_token_balances(self) -> List[TokenAmount]:
        pass

    @abstractmethod
    def get_swaps(self) -> List[PortfolioSwap]:
        pass

    @property
    def chain(self) -> str:
        return self._wallet.chain

    @classmethod
    def compute_pnl(
        cls, positions: Sequence[PortfolioSwap], base_token: TokenInfo, pricing_function: PricingFunction
    ) -> PortfolioPNL:
        """Compute profit and loss (PNL) for a sequence of portfolio swaps.

        Args:
            positions: Sequence of portfolio swaps to analyze
            base_token: Token to use as the base currency for PNL calculations
            pricing_function: Function that returns current price of an asset in terms of base token (asset_token/base_token)

        Returns:
            PortfolioPNL object containing realized and unrealized PNL details
        """
        items = sorted(positions, key=lambda x: x.block_number)
        per_asset = defaultdict(list)
        for position in items:
            if position.sold.token_info.address == base_token.address:
                per_asset[position.bought.token_info.address].append(position)
            if position.bought.token_info.address == base_token.address:
                per_asset[position.sold.token_info.address].append(position)

        result = PortfolioPNL()
        for asset, swaps in per_asset.items():
            result.add_details(
                asset,
                cls.compute_pnl_fifo_for_pair(swaps, base_token, pricing_function(asset, base_token.address)),
            )

        return result

    @classmethod
    def compute_pnl_fifo_for_pair(
        cls, swaps: List[PortfolioSwap], base_token: TokenInfo, asset_price: Decimal
    ) -> List[PortfolioPNLDetail]:
        purchases: deque[PortfolioSwap] = deque()
        bought_position: Optional[PortfolioSwap] = None
        buy_remaining = Decimal(0)
        result: List[PortfolioPNLDetail] = []
        for swap in swaps:
            if swap.sold.token_info.address == base_token.address:
                purchases.append(swap)
                continue

            sell_remaining = swap.sold.value
            while sell_remaining > 0:
                if buy_remaining <= 0 or bought_position is None:
                    try:
                        bought_position = purchases.popleft()
                    except IndexError:
                        raise RuntimeError("Missing bought position to compute PNL")
                    buy_remaining = bought_position.bought.value

                sold_quantity = min(sell_remaining, buy_remaining)
                result.append(PortfolioRealizedPNLDetail(bought_position, swap, sold_quantity))
                sell_remaining -= sold_quantity
                buy_remaining -= sold_quantity

        if buy_remaining > 0 and bought_position is not None:
            result.append(PortfolioUnrealizedPNLDetail(bought_position, asset_price, buy_remaining))

        for bought_position in purchases:
            result.append(PortfolioUnrealizedPNLDetail(bought_position, asset_price, bought_position.bought.value))

        return result


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
            portfolios.append(cls.from_chain(config.get_chain_config(chain)))
        return cls(portfolios)

    @staticmethod
    def from_chain(chain_config: ChainConfig) -> PortfolioBase:
        wallet_info = WalletInfo.from_chain_config(chain_config)
        if chain_config.chain == "solana":
            return PortfolioSolana(wallet_info, SolanaClient(chain_config), HeliusClient.from_env(), JupiterClient())
        if chain_config.chain in ["ethereum", "ethereum_sepolia", "base"]:
            return PortfolioEvm(wallet_info, EVMClient(chain_config), AlchemyClient.from_env())
        raise ValueError(f"unsupported chain {chain_config.chain}")


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
                logger.debug(f"Transfer {transfer.tx_hash} has no matching output")
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
