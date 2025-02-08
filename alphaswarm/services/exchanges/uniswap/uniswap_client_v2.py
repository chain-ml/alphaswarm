from __future__ import annotations

import logging
from decimal import Decimal
from typing import List, Tuple

from alphaswarm.config import ChainConfig, Config, TokenInfo
from alphaswarm.services.chains.evm import ZERO_ADDRESS
from alphaswarm.services.exchanges.base import Slippage
from alphaswarm.services.exchanges.uniswap.constants_v2 import (
    UNISWAP_V2_DEPLOYMENTS,
    UNISWAP_V2_FACTORY_ABI,
    UNISWAP_V2_ROUTER_ABI,
    UNISWAP_V2_VERSION,
)
from alphaswarm.services.exchanges.uniswap.uniswap_client_base import UniswapClientBase
from eth_defi.uniswap_v2.pair import fetch_pair_details
from eth_typing import ChecksumAddress
from web3.types import TxReceipt

logger = logging.getLogger(__name__)


class UniswapClientV2(UniswapClientBase):
    def __init__(self, chain_config: ChainConfig) -> None:
        super().__init__(chain_config=chain_config, version=UNISWAP_V2_VERSION)
        self._web3 = self._evm_client.client

    def _get_router(self) -> ChecksumAddress:
        return self._evm_client.to_checksum_address(UNISWAP_V2_DEPLOYMENTS[self.chain]["router"])

    def _get_factory(self) -> ChecksumAddress:
        return self._evm_client.to_checksum_address(UNISWAP_V2_DEPLOYMENTS[self.chain]["factory"])

    def _swap(
        self, base: TokenInfo, quote: TokenInfo, address: str, raw_quote_amount: int, slippage_bps: int
    ) -> List[TxReceipt]:
        """Execute a swap on Uniswap V2."""
        # Handle token approval and get fresh nonce
        approval_receipt = self._approve_token_spend(quote, raw_quote_amount)

        # Get price from V2 pair to calculate minimum output
        price = self._get_token_price(token_out=base, token_in=quote)
        if not price:
            raise ValueError(f"No V2 price found for {base.symbol}/{quote.symbol}")

        # Calculate expected output
        input_amount_decimal = quote.convert_from_wei(raw_quote_amount)
        expected_output_decimal = input_amount_decimal * price
        logger.info(f"Expected output: {expected_output_decimal} {base.symbol}")

        # Convert expected output to raw integer and apply slippage
        slippage = Slippage(slippage_bps)
        min_output_raw = slippage.calculate_minimum_amount(base.convert_to_wei(expected_output_decimal))
        logger.info(f"Minimum output with {slippage} slippage (raw): {min_output_raw}")

        # Build swap path
        path = [quote.checksum_address, base.checksum_address]

        # Build swap transaction with EIP-1559 parameters
        router_contract = self._web3.eth.contract(address=self._router, abi=UNISWAP_V2_ROUTER_ABI)
        deadline = int(self._evm_client.get_block_latest()["timestamp"] + 300)  # 5 minutes

        swap = router_contract.functions.swapExactTokensForTokens(
            raw_quote_amount,  # amount in
            min_output_raw,  # minimum amount out
            path,  # swap path
            address,  # recipient
            deadline,  # deadline
        )

        # Get gas fees
        swap_receipt = self._evm_client.process(swap, self.get_signer())
        return [approval_receipt, swap_receipt]

    def _get_token_price(self, token_out: TokenInfo, token_in: TokenInfo) -> Decimal:
        # Create factory contract instance
        factory_contract = self._web3.eth.contract(address=self._factory, abi=UNISWAP_V2_FACTORY_ABI)

        # Get pair address from factory using checksum addresses
        pair_address = factory_contract.functions.getPair(token_out.checksum_address, token_in.checksum_address).call()

        if pair_address == ZERO_ADDRESS:
            logger.warning(f"No V2 pair found for {token_out.symbol}/{token_in.symbol}")
            raise RuntimeError(f"No V2 pair found for {token_out.symbol}/{token_in.symbol}")

        # Get V2 pair details - if reverse false, mid_price = token1_amount / token0_amount
        # token0 of the pair has the lowest address. Reverse if needed
        reverse = token_out.checksum_address.lower() < token_in.checksum_address.lower()
        pair = fetch_pair_details(self._web3, pair_address, reverse_token_order=reverse)
        price = pair.get_current_mid_price()

        return price

    def _get_markets_for_tokens(self, tokens: List[TokenInfo]) -> List[Tuple[TokenInfo, TokenInfo]]:
        """Get all V2 pairs between the provided tokens."""
        markets = []
        factory = self._web3.eth.contract(address=self._factory, abi=UNISWAP_V2_FACTORY_ABI)

        # Check each possible token pair
        for i, token1 in enumerate(tokens):
            for token2 in tokens[i + 1 :]:  # Only check each pair once
                try:
                    # Get pair address from factory
                    pair_address = factory.functions.getPair(token1.checksum_address, token2.checksum_address).call()

                    if pair_address != ZERO_ADDRESS:
                        # Order tokens consistently
                        if token1.address.lower() < token2.address.lower():
                            markets.append((token1, token2))
                        else:
                            markets.append((token2, token1))

                except Exception as e:
                    logger.error(f"Error checking pair {token1.symbol}/{token2.symbol}: {str(e)}")
                    continue

        return markets

    @classmethod
    def from_config(cls, config: Config, chain: str) -> UniswapClientV2:
        return cls(config.get_chain_config(chain))
