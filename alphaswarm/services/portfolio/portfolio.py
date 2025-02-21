from __future__ import annotations

import logging
from abc import abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum, auto
from typing import Callable, Dict, Iterable, List, Optional, Self, Sequence

from solders.pubkey import Pubkey

from ...config import Config, WalletInfo
from ...core.token import TokenAmount, TokenInfo
from ..alchemy import AlchemyClient
from ..alchemy.alchemy_client import Transfer
from ..chains import EVMClient, SolanaClient

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
    def __init__(self, bought: PortfolioSwap, selling_price: Decimal, asset_sold: Decimal, is_realized: bool) -> None:
        self._bought = bought
        self._selling_price = selling_price
        self._assert_sold = asset_sold
        self._is_realized = is_realized
        self._pnl = asset_sold * (self._selling_price - self.buying_price)

    @property
    def buying_price(self) -> Decimal:
        """Buying price per assert"""
        return self._bought.sold.value / self._bought.bought.value

    @property
    def sold_amount(self) -> Decimal:
        return self._assert_sold

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
    def __init__(self, bought: PortfolioSwap, sold: PortfolioSwap, asset_sold: Decimal) -> None:
        if bought.block_number > sold.block_number:
            raise ValueError("bought block number is greater than sold block number")

        super().__init__(bought, sold.bought.value / sold.sold.value, asset_sold, is_realized=True)
        self._sold = sold


class PortfolioUnrealizedPNLDetail(PortfolioPNLDetail):
    def __init__(self, bought: PortfolioSwap, selling_price: Decimal, asset_sold: Decimal) -> None:
        super().__init__(bought, selling_price, asset_sold, is_realized=False)


@dataclass
class PortfolioSwap:
    sold: TokenAmount
    bought: TokenAmount
    hash: str
    block_number: int

    def to_short_string(self) -> str:
        return f"{self.sold.value} {self.sold.token_info.symbol} -> {self.bought.value} {self.bought.token_info.symbol} ({self.sold.token_info.chain} {self.block_number} {self.hash})"


# A pricing function that returns the price in second token address for each first token address
PricingFunction = Callable[[str, str], Decimal]


class PortfolioBase:
    def __init__(self, wallet: WalletInfo) -> None:
        self._wallet = wallet

    @abstractmethod
    def get_token_balances(self) -> List[TokenAmount]:
        pass

    @property
    def chain(self) -> str:
        return self._wallet.chain

    @classmethod
    def compute_pnl(
        cls, positions: Sequence[PortfolioSwap], base_token: TokenInfo, pricing_function: PricingFunction
    ) -> PortfolioPNL:
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

    def get_positions(self) -> List[PortfolioSwap]:
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
    def __init__(self, wallet: WalletInfo, solana_client: SolanaClient) -> None:
        super().__init__(wallet)
        self._solana_client = solana_client

    def get_token_balances(self) -> List[TokenAmount]:
        return self._solana_client.get_all_token_balances(Pubkey.from_string(self._wallet.address))
