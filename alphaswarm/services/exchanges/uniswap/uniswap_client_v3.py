import logging
from datetime import timedelta
from decimal import Decimal
from typing import Dict

from alphaswarm.config import Config, TokenInfo
from alphaswarm.services.exchanges.uniswap.constants_v3 import (
    UNISWAP_V3_DEPLOYMENTS,
    UNISWAP_V3_ROUTER2_ABI,
    UNISWAP_V3_ROUTER_ABI,
)
from alphaswarm.services.exchanges.uniswap.uniswap_client import UniswapClient
from eth_defi.confirmation import wait_transactions_to_complete
from eth_defi.uniswap_v3.price import get_onchain_price
from hexbytes import HexBytes

logger = logging.getLogger(__name__)


class UniswapClientV3(UniswapClient):
    def __init__(self, config: Config, chain: str):
        super().__init__(config, chain, "v3")

    def _initialize(self) -> bool:
        if self.chain in UNISWAP_V3_DEPLOYMENTS:  # Check for V3 support
            deployment_data_v3 = UNISWAP_V3_DEPLOYMENTS[self.chain]

            logger.info(f"Initializing Uniswap V3 on {self.chain} with:")
            logger.info(f"  Factory: {deployment_data_v3['factory']}")
            logger.info(f"  Router: {deployment_data_v3['router']}")
            logger.info(f"  Position Manager: {deployment_data_v3['position_manager']}")
            logger.info(f"  Quoter: {deployment_data_v3['quoter']}")

            self._router = deployment_data_v3["router"]
            self._factory = deployment_data_v3["factory"]
            return True

        return False

    def _swap(
        self, base: TokenInfo, quote: TokenInfo, address: str, raw_amount: int, slippage_bps: int
    ) -> Dict[HexBytes, Dict]:
        """Execute a swap on Uniswap V3."""
        # Handle token approval and get fresh nonce
        nonce, approval_receipt = self._approve_token_spend(quote, address, raw_amount)

        # Build a swap transaction
        pool_details = self._get_v3_pool(base_token=base, quote_token=quote)
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
            "tokenIn": self._web3.to_checksum_address(quote.address),
            "tokenOut": self._web3.to_checksum_address(base.address),
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
        router_contract = self._web3.eth.contract(address=self._web3.to_checksum_address(self._router), abi=router_abi)
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
