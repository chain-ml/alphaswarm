import logging
from datetime import timedelta
from decimal import Decimal
from typing import Dict, List, Tuple

from alphaswarm.config import Config, TokenInfo
from alphaswarm.services.exchanges.uniswap.constants_v2 import (
    UNISWAP_V2_DEPLOYMENTS,
    UNISWAP_V2_FACTORY_ABI,
    UNISWAP_V2_ROUTER_ABI,
)
from alphaswarm.services.exchanges.uniswap.uniswap_client import ZERO_ADDRESS, UniswapClientBase
from eth_defi.confirmation import wait_transactions_to_complete
from eth_defi.uniswap_v2.pair import fetch_pair_details
from eth_typing import ChecksumAddress
from eth_utils import to_checksum_address
from hexbytes import HexBytes

logger = logging.getLogger(__name__)


class UniswapClientV2(UniswapClientBase):
    def __init__(self, config: Config, chain: str):
        super().__init__(config, chain, "v2")

    def _get_router(self, chain: str) -> ChecksumAddress:
        return to_checksum_address(UNISWAP_V2_DEPLOYMENTS[chain]["router"])

    def _get_factory(self, chain: str) -> ChecksumAddress:
        return to_checksum_address(UNISWAP_V2_DEPLOYMENTS[chain]["factory"])

    def _swap(
        self, base: TokenInfo, quote: TokenInfo, address: str, raw_quote_amount: int, slippage_bps: int
    ) -> Dict[HexBytes, Dict]:
        """Execute a swap on Uniswap V2."""
        # Handle token approval and get fresh nonce
        nonce, approval_receipt = self._approve_token_spend(quote, address, raw_quote_amount)

        # Get price from V2 pair to calculate minimum output
        price = self._get_token_price(base_token=base, quote_token=quote)
        if not price:
            raise ValueError(f"No V2 price found for {base.symbol}/{quote.symbol}")

        # Calculate expected output
        input_amount_decimal = Decimal(raw_quote_amount) / (Decimal(10) ** quote.decimals)
        expected_output_decimal = input_amount_decimal * price
        logger.info(f"Expected output: {expected_output_decimal} {base.symbol}")

        # Convert expected output to raw integer and apply slippage
        slippage_multiplier = Decimal(1) - (Decimal(slippage_bps) / Decimal(10000))
        min_output_raw = int(expected_output_decimal * (10**base.decimals) * slippage_multiplier)
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
        max_fee_per_gas, _, priority_fee, gas_limit = self._get_gas_fees()

        tx_2 = swap.build_transaction(
            {
                "gas": gas_limit,
                "chainId": self._web3.eth.chain_id,
                "from": address,
                "nonce": nonce,
                "maxFeePerGas": max_fee_per_gas,
                "maxPriorityFeePerGas": priority_fee,
            }
        )

        # Send swap transaction
        tx_hash_2 = self._web3.eth.send_transaction(tx_2)
        logger.info(f"Waiting for swap transaction {tx_hash_2.hex()} to be mined...")
        swap_receipt = wait_transactions_to_complete(
            self._web3,
            [tx_hash_2],
            max_timeout=timedelta(minutes=2.5),
            confirmation_block_count=1,
        )

        return {**approval_receipt, **swap_receipt}

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
