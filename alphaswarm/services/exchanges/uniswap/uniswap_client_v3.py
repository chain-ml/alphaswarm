import logging
from datetime import timedelta
from decimal import Decimal
from typing import Dict, List, Tuple

from alphaswarm.config import Config, TokenInfo
from alphaswarm.services.exchanges.uniswap.constants_v3 import (
    UNISWAP_V3_DEPLOYMENTS,
    UNISWAP_V3_FACTORY_ABI,
    UNISWAP_V3_ROUTER2_ABI,
    UNISWAP_V3_ROUTER_ABI,
)
from alphaswarm.services.exchanges.uniswap.uniswap_client import ZERO_ADDRESS, UniswapClient
from cchecksum import to_checksum_address
from eth_defi.confirmation import wait_transactions_to_complete
from eth_defi.uniswap_v3.pool import PoolDetails, fetch_pool_details
from eth_defi.uniswap_v3.price import get_onchain_price
from eth_typing import ChecksumAddress
from hexbytes import HexBytes

logger = logging.getLogger(__name__)


class UniswapClientV3(UniswapClient):
    def __init__(self, config: Config, chain: str):
        super().__init__(config, chain, "v3")

    def _get_router(self, chain: str) -> ChecksumAddress:
        return to_checksum_address(UNISWAP_V3_DEPLOYMENTS[chain]["router"])

    def _get_factory(self, chain: str) -> ChecksumAddress:
        return to_checksum_address(UNISWAP_V3_DEPLOYMENTS[chain]["factory"])

    def _swap(
        self, base: TokenInfo, quote: TokenInfo, address: str, raw_amount: int, slippage_bps: int
    ) -> Dict[HexBytes, Dict]:
        """Execute a swap on Uniswap V3."""
        # Handle token approval and get fresh nonce
        nonce, approval_receipt = self._approve_token_spend(quote, address, raw_amount)

        # Build a swap transaction
        pool_details = self._get_pool(base_token=base, quote_token=quote)
        if not pool_details:
            raise ValueError(f"No V3 pool found for {base.symbol}/{quote.symbol}")

        logger.info(f"Using Uniswap V3 pool at address: {pool_details.address} (raw fee tier: {pool_details.raw_fee})")

        # Get the on-chain price from the pool and reverse if necessary
        reverse = base.address.lower() == pool_details.token0.address.lower()
        raw_price = get_onchain_price(self._web3, pool_details.address, reverse_token_order=reverse)
        logger.info(f"Pool raw price: {raw_price} ({quote.symbol} per {base.symbol})")

        # Convert to decimal for calculations
        price = Decimal(str(raw_price))
        input_amount_decimal = Decimal(str(raw_amount)) / (Decimal("10") ** quote.decimals)
        logger.info(f"Actual input amount: {input_amount_decimal} {quote.symbol}")

        # Calculate expected output
        expected_output_decimal = input_amount_decimal * price
        logger.info(f"Expected output: {expected_output_decimal} {base.symbol}")

        # Convert expected output to raw integer
        raw_output = int(expected_output_decimal * Decimal(10**base.decimals))
        logger.info(f"Expected output amount (raw): {raw_output}")

        # Calculate price impact
        pool_liquidity = pool_details.pool.functions.liquidity().call()
        logger.info(f"Pool liquidity: {pool_liquidity}")

        # Estimate price impact (simplified)
        price_impact = (raw_amount * 10000) / pool_liquidity  # in bps
        logger.info(f"Estimated price impact: {price_impact:.2f} bps")

        # Check if price impact is too high relative to slippage
        # Price impact should be significantly lower than slippage to leave room for market moves
        if price_impact > (slippage_bps * 0.67):  # If price impact is more than 2/3 of slippage
            logger.warning(
                f"WARNING: Price impact ({price_impact:.2f} bps) is more than 2/3 of slippage tolerance ({slippage_bps} bps)"
            )
            logger.warning(
                "This leaves little room for market price changes between transaction submission and execution"
            )

        # Apply slippage
        slippage_multiplier = Decimal("1") - (Decimal(slippage_bps) / Decimal(10000))
        min_output_raw = int(raw_output * slippage_multiplier)
        logger.info(f"Minimum output with {slippage_bps} bps slippage (raw): {min_output_raw}")

        # Build swap parameters for `exactInputSingle`
        params = {
            "tokenIn": quote.checksum_address,
            "tokenOut": base.checksum_address,
            "fee": pool_details.raw_fee,
            "recipient": self._web3.to_checksum_address(address),
            "deadline": int(self._web3.eth.get_block("latest")["timestamp"] + 300),
            "amountIn": raw_amount,
            "amountOutMinimum": min_output_raw,
            "sqrtPriceLimitX96": 0,
        }
        logger.info("Built exactInputSingle parameters:")
        for k, v in params.items():
            logger.info(f"  {k}: {v}")

        # Build swap transaction with EIP-1559 parameters
        router_abi = UNISWAP_V3_ROUTER2_ABI if self.chain in ["base", "ethereum_sepolia"] else UNISWAP_V3_ROUTER_ABI
        router_contract = self._web3.eth.contract(address=self._router, abi=router_abi)
        swap = router_contract.functions.exactInputSingle(params)

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
        """Get the current price from a Uniswap V3 pool for a token pair.

        Finds the first available pool for the token pair and gets the current price.
        The price is returned in terms of base/quote (how much quote token per base token).

        Args:
            base_token: Base token info (token being priced)
            quote_token: Quote token info (denominator token)

        Returns:
            Decimal: Current price in base/quote terms, or None if no pool exists
            or there was an error getting the price

        Note:
            Uses the pool with the most liquidity.
            Uses the pool with the most liquidity.
        """
        pool_details = self._get_pool(base_token=base_token, quote_token=quote_token)
        # Get raw price from pool
        reverse = quote_token.address.lower() == pool_details.token0.address.lower()
        raw_price = get_onchain_price(self._web3, pool_details.address, reverse_token_order=reverse)

        return raw_price

    def _get_pool(self, *, base_token: TokenInfo, quote_token: TokenInfo) -> PoolDetails:
        """Find the Uniswap V3 pool with highest liquidity for a token pair.

        Checks all configured fee tiers and returns the pool with the highest liquidity.
        The pool details include addresses, tokens, and fee information.

        Args:
            base_token: Base token info (token being priced)
            quote_token: Quote token info (denominator token)

        Returns:
            PoolDetails: Details about the pool with highest liquidity, or None if no pool exists
            or there was an error finding a pool
        """
        settings = self.config.get_venue_settings_uniswap_v3()
        factory_contract = self._web3.eth.contract(address=self._factory, abi=UNISWAP_V3_FACTORY_ABI)

        max_liquidity = 0
        best_pool_details = None

        # Check all fee tiers to find pool with highest liquidity
        for fee in settings.fee_tiers:
            try:
                pool_address = factory_contract.functions.getPool(base_token.address, quote_token.address, fee).call()
                if pool_address == ZERO_ADDRESS:
                    continue

                # Get pool details to access the contract
                pool_details = fetch_pool_details(self._web3, pool_address)
                if not pool_details:
                    continue

                # Check liquidity
                liquidity = pool_details.pool.functions.liquidity().call()
                logger.info(f"Pool {pool_address} (fee tier {fee} bps) liquidity: {liquidity}")

                # Update best pool if this one has more liquidity
                if liquidity > max_liquidity:
                    max_liquidity = liquidity
                    best_pool_details = pool_details

            except Exception:
                logger.exception(f"Failed to get pool for fee tier {fee}")
                continue

        if best_pool_details:
            logger.info(
                f"Selected pool with highest liquidity: {best_pool_details.address} (liquidity: {max_liquidity})"
            )
            return best_pool_details

        logger.warning(f"No V3 pool found for {base_token.symbol}/{quote_token.symbol}")
        raise RuntimeError(f"No pool found for {base_token.symbol}/{quote_token.symbol}")

    def _get_markets_for_tokens(self, tokens: List[TokenInfo]) -> List[Tuple[TokenInfo, TokenInfo]]:
        """Get all V3 pools between the provided tokens."""
        markets = []
        factory = self._web3.eth.contract(address=self._factory, abi=UNISWAP_V3_FACTORY_ABI)

        # Get fee tiers from settings
        settings = self.config.get_venue_settings_uniswap_v3()
        fee_tiers = settings.fee_tiers

        # Check each possible token pair
        for i, token1 in enumerate(tokens):
            for token2 in tokens[i + 1 :]:  # Only check each pair once
                try:
                    # Check each fee tier
                    for fee in fee_tiers:
                        pool_address = factory.functions.getPool(token1.address, token2.address, fee).call()

                        if pool_address != ZERO_ADDRESS:
                            # Order tokens consistently
                            if token1.address.lower() < token2.address.lower():
                                markets.append((token1, token2))
                            else:
                                markets.append((token2, token1))
                            # Break after finding first pool for this pair
                            break

                except Exception as e:
                    logger.error(f"Error checking pool {token1.symbol}/{token2.symbol}: {str(e)}")
                    continue

        return markets
