import logging
from datetime import timedelta
from decimal import Decimal
from typing import Dict

from alphaswarm.config import Config, TokenInfo
from alphaswarm.services.exchanges.uniswap.constants_v2 import (
    UNISWAP_V2_DEPLOYMENTS,
    UNISWAP_V2_INIT_CODE_HASH,
    UNISWAP_V2_ROUTER_ABI,
)
from alphaswarm.services.exchanges.uniswap.uniswap_client import UniswapClient
from eth_defi.confirmation import wait_transactions_to_complete
from hexbytes import HexBytes

logger = logging.getLogger(__name__)


class UniswapClientV2(UniswapClient):
    def __init__(self, config: Config, chain: str):
        super().__init__(config, chain, "v2")

    def _initialize(self) -> bool:
        if self.chain in UNISWAP_V2_DEPLOYMENTS:  # Check for V2 support
            deployment_data_v2 = UNISWAP_V2_DEPLOYMENTS[self.chain]
            init_code_hash = UNISWAP_V2_INIT_CODE_HASH.get(self.chain)
            if not init_code_hash:
                raise ValueError(f"No V2 init code hash found for chain: {self.chain}")

            logger.info(f"Initializing Uniswap V2 on {self.chain} with:")
            logger.info(f"  Factory: {deployment_data_v2['factory']}")
            logger.info(f"  Router: {deployment_data_v2['router']}")
            logger.info(f"  Init Code Hash: {init_code_hash}")

            self._factory = deployment_data_v2["factory"]
            self._router = deployment_data_v2["router"]
            return True

        return False

    def _swap(
        self, base: TokenInfo, quote: TokenInfo, address: str, raw_amount: int, slippage_bps: int
    ) -> Dict[HexBytes, Dict]:
        """Execute a swap on Uniswap V2."""
        # Handle token approval and get fresh nonce
        nonce, approval_receipt = self._approve_token_spend(quote, address, raw_amount)

        # Get price from V2 pair to calculate minimum output
        price = self._get_v2_price(base_token=base, quote_token=quote)
        if not price:
            raise ValueError(f"No V2 price found for {base.symbol}/{quote.symbol}")

        # Calculate expected output
        input_amount_decimal = Decimal(raw_amount) / (Decimal(10) ** quote.decimals)
        expected_output_decimal = input_amount_decimal * price
        logger.info(f"Expected output: {expected_output_decimal} {base.symbol}")

        # Convert expected output to raw integer and apply slippage
        slippage_multiplier = Decimal(1) - (Decimal(slippage_bps) / Decimal(10000))
        min_output_raw = int(expected_output_decimal * (10**base.decimals) * slippage_multiplier)
        logger.info(f"Minimum output with {slippage_bps} bps slippage (raw): {min_output_raw}")

        # Build swap path
        path = [self._web3.to_checksum_address(quote.address), self._web3.to_checksum_address(base.address)]

        # Build swap transaction with EIP-1559 parameters
        router_contract = self._web3.eth.contract(
            address=self._web3.to_checksum_address(self._router), abi=UNISWAP_V2_ROUTER_ABI
        )
        deadline = int(self._web3.eth.get_block("latest")["timestamp"] + 300)  # 5 minutes

        swap = router_contract.functions.swapExactTokensForTokens(
            raw_amount,  # amount in
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
