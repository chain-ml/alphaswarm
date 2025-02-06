import logging
from decimal import Decimal
from typing import List, Tuple

from alphaswarm.config import Config, TokenInfo
from alphaswarm.services.chains.evm import ZERO_ADDRESS
from alphaswarm.services.exchanges.uniswap.constants_v2 import (
    UNISWAP_V2_DEPLOYMENTS,
    UNISWAP_V2_FACTORY_ABI,
    UNISWAP_V2_ROUTER_ABI,
)
from alphaswarm.services.exchanges.uniswap.uniswap_client_base import UniswapClientBase
from eth_defi.uniswap_v2.pair import fetch_pair_details
from eth_typing import ChecksumAddress
from web3.types import TxReceipt

logger = logging.getLogger(__name__)


class UniswapClientV2(UniswapClientBase):
    def __init__(self, config: Config, chain: str):
        super().__init__(config, chain, "v2")

    def _get_router(self, chain: str) -> ChecksumAddress:
        return self._evm_client.to_checksum_address(UNISWAP_V2_DEPLOYMENTS[chain]["router"])

    def _get_factory(self, chain: str) -> ChecksumAddress:
        return self._evm_client.to_checksum_address(UNISWAP_V2_DEPLOYMENTS[chain]["factory"])

    def _swap(
        self, base: TokenInfo, quote: TokenInfo, address: str, raw_quote_amount: int, slippage_bps: int
    ) -> List[TxReceipt]:
        """Execute a swap on Uniswap V2."""
        # Handle token approval and get fresh nonce
        approval_receipt = self._approve_token_spend(quote, raw_quote_amount)

        # Get price from V2 pair to calculate minimum output
        price = self._get_token_price(base_token=base, quote_token=quote)
        if not price:
            raise ValueError(f"No V2 price found for {base.symbol}/{quote.symbol}")

        # Calculate expected output
        input_amount_decimal = quote.convert_from_wei(raw_quote_amount)
        expected_output_decimal = input_amount_decimal * price
        logger.info(f"Expected output: {expected_output_decimal} {base.symbol}")

        # Convert expected output to raw integer and apply slippage
        slippage_multiplier = Decimal(1) - (Decimal(slippage_bps) / Decimal(10000))
        min_output_raw = base.convert_to_wei(expected_output_decimal) * slippage_multiplier
        logger.info(f"Minimum output with {slippage_bps} bps slippage (raw): {min_output_raw}")

        # Build swap path
        path = [quote.checksum_address, base.checksum_address]

        # Build swap transaction with EIP-1559 parameters
        router_contract = self._web3.eth.contract(address=self._router, abi=UNISWAP_V2_ROUTER_ABI)
        deadline = int(self._web3.eth.get_block("latest")["timestamp"] + 300)  # 5 minutes

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

    def _get_token_price(self, base_token: TokenInfo, quote_token: TokenInfo) -> Decimal:
        """Get the current price from a Uniswap V2 pool for a token pair.

        Finds the V2 pool for the token pair and gets the current mid price.
        The price is returned in terms of base/quote.

        Args:
            base_token: Base token info (token being priced)
            quote_token: Quote token info (denominator token)

        Returns:
            Decimal: Current mid price in base/quote terms, or None if no pool exists
            or there was an error getting the price
        """
        # Create factory contract instance
        factory_contract = self._web3.eth.contract(address=self._factory, abi=UNISWAP_V2_FACTORY_ABI)

        # Get pair address from factory using checksum addresses
        pair_address = factory_contract.functions.getPair(
            base_token.checksum_address, quote_token.checksum_address
        ).call()

        if pair_address == ZERO_ADDRESS:
            logger.warning(f"No V2 pair found for {base_token.symbol}/{quote_token.symbol}")
            raise RuntimeError(f"No V2 pair found for {base_token.symbol}/{quote_token.symbol}")

        # Get V2 pair details - we want price in base/quote terms
        # If base_token is token1, we need reverse=True to get base/quote
        reverse = base_token.checksum_address.lower() > quote_token.checksum_address.lower()
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
