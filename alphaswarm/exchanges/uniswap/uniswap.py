import datetime
import decimal
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from alphaswarm.chains.factory import Web3ClientFactory
from alphaswarm.config import Config, TokenInfo
from alphaswarm.exchanges.base import DEXClient, SwapResult
from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_defi.confirmation import wait_transactions_to_complete
from eth_defi.provider.multi_provider import MultiProviderWeb3, create_multi_provider_web3
from eth_defi.revert_reason import fetch_transaction_revert_reason
from eth_defi.uniswap_v2.pair import fetch_pair_details
from eth_defi.uniswap_v3.pool import PoolDetails, fetch_pool_details
from eth_defi.uniswap_v3.price import get_onchain_price as get_onchain_price_v3
from eth_typing import HexAddress
from hexbytes import HexBytes
from web3.middleware.signing import construct_sign_and_send_raw_middleware

from .constants import (
    ERC20_ABI,
    UNISWAP_V2_DEPLOYMENTS,
    UNISWAP_V2_FACTORY_ABI,
    UNISWAP_V2_INIT_CODE_HASH,
    UNISWAP_V2_ROUTER_ABI,
    UNISWAP_V3_DEPLOYMENTS,
    UNISWAP_V3_FACTORY_ABI,
    UNISWAP_V3_ROUTER2_ABI,
    UNISWAP_V3_ROUTER_ABI,
)

# Set up logger
logger = logging.getLogger(__name__)

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
DEFAULT_GAS_LIMIT = 200_000  # Default gas limit for transactions


class UniswapClient(DEXClient):
    def __init__(self, config: Config, chain: str, version: str) -> None:
        super().__init__(config, chain)
        self.version = version
        self._config = config
        self._router: Optional[str] = None
        self._factory: Optional[str] = None
        self._position_manager = None
        self._quoter = None
        self._blockchain_client = Web3ClientFactory.get_instance().get_client(self.chain, self.config)
        self._web3: MultiProviderWeb3 = create_multi_provider_web3(self.config.get_chain_config(self.chain).rpc_url)

        logger.info("Created UniswapClient instance (uninitialized)")
        self._initialize()

    def initialize(self) -> None:
        """Initialize the client with version and chain information.
        This should be called by DEXFactory after creating the instance."""
        self._initialize()
        logger.info(f"Finished initializing Uniswap-Client {self.version} on {self.chain}")

    def _initialize(self) -> None:

        # Initialize contract and deployment data
        if self.version == "v2" and self.chain in UNISWAP_V2_DEPLOYMENTS:  # Check for V2 support
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
        elif self.version == "v3" and self.chain in UNISWAP_V3_DEPLOYMENTS:  # Check for V3 support
            deployment_data_v3 = UNISWAP_V3_DEPLOYMENTS[self.chain]

            logger.info(f"Initializing Uniswap V3 on {self.chain} with:")
            logger.info(f"  Factory: {deployment_data_v3['factory']}")
            logger.info(f"  Router: {deployment_data_v3['router']}")
            logger.info(f"  Position Manager: {deployment_data_v3['position_manager']}")
            logger.info(f"  Quoter: {deployment_data_v3['quoter']}")

            self._router = deployment_data_v3["router"]
            self._factory = deployment_data_v3["factory"]
        else:
            raise ValueError(f"Uniswap {self.version} not supported on chain: {self.chain}")

    @staticmethod
    def _get_final_swap_amount_received(
        swap_receipt: dict[str, Any], token_address: HexAddress, user_address: str, token_decimals: int
    ) -> float:
        """Calculate the final amount of tokens received from a swap by parsing Transfer events.

        Looks through the transaction receipt logs for Transfer events where the recipient matches
        the user's address and sums up the transferred amounts.

        Args:
            swap_receipt (dict): The transaction receipt from the swap
            token_address (HexAddress): Hexed Address of the token to track transfers for
            token_address (HexAddress): Hexed Address of the token to track transfers for
            user_address (str): Address of the user receiving the tokens
            token_decimals (int): Number of decimals for the token

        Returns:
            float: Total amount of tokens received, normalized by token decimals
        """

        TRANSFER_SIG = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

        total_received = 0  # Might be multiple logs if multi-hop or partial fills

        for log in swap_receipt["logs"]:
            if (
                log["address"].lower() == token_address.lower()
                and len(log["topics"]) == 3
                and log["topics"][0].hex().lower() == TRANSFER_SIG
            ):
                # Decode 'from' and 'to'
                # from_addr = "0x" + log["topics"][1].hex()[-40:]
                to_addr = "0x" + log["topics"][2].hex()[-40:]

                if to_addr.lower() == user_address.lower():
                    raw_amount = int(log["data"].hex(), 16)
                    total_received += raw_amount

        # Convert to human-readable amount
        return float(total_received) / (10**token_decimals)

    def swap(
        self,
        base_token: TokenInfo,
        quote_token: TokenInfo,
        quote_amount: float,
        slippage_bps: int = 100,
    ) -> SwapResult:
        """Execute a token swap on Uniswap.

        Args:
            base_token: TokenInfo object for the token being sold
            quote_token: TokenInfo object for the token being bought
            quote_amount: Amount of quote_token to spend (output amount)
            slippage_bps: Maximum allowed slippage in basis points (1 bp = 0.01%)
            base_token: TokenInfo object for the token being sold
            quote_token: TokenInfo object for the token being bought
            quote_amount: Amount of quote_token to spend (output amount)
            slippage_bps: Maximum allowed slippage in basis points (1 bp = 0.01%)

        Returns:
            SwapResult: Result object containing success status, transaction hash and any error details

        Note:
            Private key is read from environment variables via config for the specified chain.
        """
        private_key = self._config.get_chain_config(self.chain).private_key
        swap_result = self._swap(base_token, quote_token, quote_amount, private_key, slippage_bps)
        return swap_result

    def _swap(
        self,
        base_token: TokenInfo,
        quote_token: TokenInfo,
        quote_amount: float,
        wallet_key: str,
        slippage_bps: int = 100,
    ) -> SwapResult:
        """Execute a token swap on Uniswap."""
        logger.info(f"Initiating token swap for {quote_token.symbol} to {base_token.symbol}")

        # Set up account
        account: LocalAccount = Account.from_key(wallet_key)
        wallet_address = account.address
        logger.info(f"Wallet address: {wallet_address}")

        # Enable eth_sendTransaction using this private key
        self._web3.middleware_onion.add(construct_sign_and_send_raw_middleware(account))

        # Create contract instances
        base_contract = self._web3.eth.contract(address=base_token.checksum_address, abi=ERC20_ABI)
        quote_contract = self._web3.eth.contract(address=quote_token.checksum_address, abi=ERC20_ABI)

        # Gas balance
        gas_balance = self._web3.eth.get_balance(account.address)

        # Log balances
        base_balance = base_contract.functions.balanceOf(wallet_address).call() / (10**base_token.decimals)
        quote_balance = quote_contract.functions.balanceOf(wallet_address).call() / (10**quote_token.decimals)
        eth_balance = gas_balance / (10**18)

        logger.info(f"Balance of {base_token.symbol}: {base_balance:,.8f}")
        logger.info(f"Balance of {quote_token.symbol}: {quote_balance:,.8f}")
        logger.info(f"ETH balance for gas: {eth_balance:,.6f}")

        assert quote_balance > 0, f"Cannot perform swap, as you have zero {quote_token.symbol} needed to swap"

        try:
            decimal_amount = Decimal(quote_amount)
        except (ValueError, decimal.InvalidOperation) as e:
            raise AssertionError(f"Not a good decimal amount: {quote_amount}") from e

        raw_amount = int(decimal_amount * (10**quote_token.decimals))

        # Each DEX trade is two transactions
        # 1) ERC-20.approve()
        # 2) swap (various functions)

        if self.version == "v3":
            receipts = self._swap_v3(base_token, quote_token, wallet_address, raw_amount, slippage_bps)
        elif self.version == "v2":
            receipts = self._swap_v2(base_token, quote_token, wallet_address, raw_amount, slippage_bps)
        else:
            raise ValueError(f"Unsupported Uniswap version: {self.version}")
        # Check for transaction failure and display revert reason
        for completed_tx_hash, receipt in receipts.items():
            if receipt.get("status") == 0:
                revert_reason = fetch_transaction_revert_reason(self._web3, completed_tx_hash)
                logger.error(f"Transaction {completed_tx_hash.hex()} failed because of: {revert_reason}")
                return SwapResult(
                    success=False,
                    base_amount=0,
                    quote_amount=quote_amount,
                    tx_hash=completed_tx_hash.hex(),
                    error=revert_reason,
                )

        # Get the actual amount of base token received from the swap receipt
        swap_receipt = receipts[list(receipts.keys())[1]]
        base_amount = self._get_final_swap_amount_received(
            swap_receipt, self._web3.to_checksum_address(base_token.address), wallet_address, base_token.decimals
        )

        return SwapResult(
            success=True,
            base_amount=base_amount,
            quote_amount=quote_amount,
            tx_hash=list(receipts.keys())[1].hex(),  # Return the swap tx hash, not the approve tx
            error=None,
        )

    def _get_gas_fees(self) -> tuple[int, int, int, int]:
        """Calculate gas fees for transactions and get gas limit from config.

        Returns:
            tuple[int, int, int, int]: (max_fee_per_gas, base_fee, priority_fee, gas_limit)
        """
        # Get current base fee and priority fee
        latest_block = self._web3.eth.get_block("latest")
        base_fee = latest_block.get("baseFeePerGas", 0)  # Use get() with default value
        if base_fee == 0:
            logger.warning(
                "BaseFeePerGas set to 0 - this may indicate an issue with the RPC endpoint or chain configuration"
            )
        # Max priority fee is computed and set to likely include transaction in next block
        # TODO: Could read from config for advanced users (e.g. cheap/slow vs expensive/fast)
        priority_fee = self._web3.eth.max_priority_fee

        logger.info(f"Current base fee: {base_fee} wei")
        logger.info(f"Current priority fee: {priority_fee} wei")

        # Set max fees (base_fee * 2 to allow for base fee increase)
        max_fee_per_gas = base_fee * 2 + priority_fee
        logger.info(f"Setting max fee per gas to: {max_fee_per_gas} wei")

        # Get gas limit from chain config
        chain_config = self.config.get_chain_config(self.chain)
        if chain_config.gas_settings:
            gas_limit = chain_config.gas_settings.gas_limit
            logger.info(f"Using gas limit from config: {gas_limit}")
        else:
            gas_limit = DEFAULT_GAS_LIMIT
            logger.info(f"No gas settings in config, using default gas limit: {gas_limit}")

        return max_fee_per_gas, base_fee, priority_fee, gas_limit

    def _approve_token_spend(self, quote: TokenInfo, address: str, raw_amount: int) -> tuple[int, Dict[HexBytes, Dict]]:
        """Handle token approval and return fresh nonce and approval receipt.

        Args:
            quote: Quote token info
            address: Wallet address
            raw_amount: Raw amount to approve

        Returns:
            tuple[int, Dict[HexBytes, Dict]]: (nonce, approval_receipt)

        Raises:
            ValueError: If approval transaction fails
        """
        # Create quote token contract instance
        quote_contract = self._web3.eth.contract(address=quote.checksum_address, abi=ERC20_ABI)

        # Uniswap router must be allowed to spend our quote token
        approve = quote_contract.functions.approve(self._web3.to_checksum_address(self._router), raw_amount)

        # Get gas fees
        max_fee_per_gas, _, priority_fee, gas_limit = self._get_gas_fees()

        # Build approval transaction with EIP-1559 parameters
        tx_1 = approve.build_transaction(
            {
                "gas": gas_limit,
                "chainId": self._web3.eth.chain_id,
                "from": address,
                "maxFeePerGas": max_fee_per_gas,
                "maxPriorityFeePerGas": priority_fee,
            }
        )

        # Send approval and wait for it to be mined
        try:
            tx_hash_1 = self._web3.eth.send_transaction(tx_1)
            logger.info(f"Waiting for approval transaction {tx_hash_1.hex()} to be mined...")
            approval_receipt = wait_transactions_to_complete(
                self._web3,
                [tx_hash_1],
                max_timeout=datetime.timedelta(minutes=2.5),
                confirmation_block_count=2,
            )

            if approval_receipt[tx_hash_1]["status"] == 0:
                raise ValueError("Approval transaction failed")

        except Exception as e:
            logger.error(f"Approval transaction failed: {str(e)}")
            raise ValueError(f"Failed to approve token spend: {str(e)}")

        # Get fresh nonce after approval
        nonce = self._web3.eth.get_transaction_count(address)
        return nonce, approval_receipt

    def _swap_v2(
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
        input_amount_decimal = Decimal(str(raw_amount)) / (Decimal("10") ** quote.decimals)
        expected_output_decimal = input_amount_decimal * price
        logger.info(f"Expected output: {expected_output_decimal} {base.symbol}")

        # Convert expected output to raw integer and apply slippage
        slippage_multiplier = Decimal("1") - (Decimal(str(slippage_bps)) / Decimal("10000"))
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
            max_timeout=datetime.timedelta(minutes=2.5),
            confirmation_block_count=1,
        )

        return {**approval_receipt, **swap_receipt}

    def _swap_v3(
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
        raw_price = get_onchain_price_v3(self._web3, pool_details.address, reverse_token_order=reverse)
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
        slippage_multiplier = Decimal("1") - (Decimal(str(slippage_bps)) / Decimal("10000"))
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
            max_timeout=datetime.timedelta(minutes=2.5),
            confirmation_block_count=1,
        )

        return {**approval_receipt, **swap_receipt}

    def _get_v2_price(self, *, base_token: TokenInfo, quote_token: TokenInfo) -> Optional[Decimal]:
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
        try:
            # Create factory contract instance
            factory_contract = self._web3.eth.contract(
                address=self._web3.to_checksum_address(self._factory), abi=UNISWAP_V2_FACTORY_ABI
            )

            # Get pair address from factory using checksum addresses
            pair_address = factory_contract.functions.getPair(
                base_token.checksum_address, quote_token.checksum_address
            ).call()

            if pair_address == ZERO_ADDRESS:
                logger.warning(f"No V2 pair found for {base_token.symbol}/{quote_token.symbol}")
                return None

            # Get V2 pair details - we want price in base/quote terms
            # If base_token is token1, we need reverse=True to get base/quote
            reverse = base_token.checksum_address.lower() > quote_token.checksum_address.lower()
            pair = fetch_pair_details(self._web3, pair_address, reverse_token_order=reverse)
            price = pair.get_current_mid_price()

            return price

        except Exception as e:
            logger.error(f"Error getting V2 price: {str(e)}")
            return None

    def _get_v3_pool(self, *, base_token: TokenInfo, quote_token: TokenInfo) -> Optional[PoolDetails]:
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
        try:
            settings = self.config.get_venue_settings_uniswap_v3()
            factory_contract = self._web3.eth.contract(
                address=self._web3.to_checksum_address(self._factory), abi=UNISWAP_V3_FACTORY_ABI
            )

            max_liquidity = 0
            best_pool_details = None

            # Check all fee tiers to find pool with highest liquidity
            for fee in settings.fee_tiers:
                try:
                    pool_address = factory_contract.functions.getPool(
                        base_token.address, quote_token.address, fee
                    ).call()
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

                except Exception as e:
                    logger.debug(f"Failed to get pool for fee tier {fee}: {str(e)}")
                    continue

            if best_pool_details:
                logger.info(
                    f"Selected pool with highest liquidity: {best_pool_details.address} (liquidity: {max_liquidity})"
                )
                return best_pool_details

            logger.warning(f"No V3 pool found for {base_token.symbol}/{quote_token.symbol}")
            return None

        except Exception as e:
            logger.error(f"Error finding V3 pool: {str(e)}")
            return None

    def _get_v3_price(self, *, base_token: TokenInfo, quote_token: TokenInfo) -> Optional[Decimal]:
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
        try:
            pool_details = self._get_v3_pool(base_token=base_token, quote_token=quote_token)
            if pool_details is None:
                raise ValueError("pool details not found for Uniswap V3")
            # Get raw price from pool
            reverse = quote_token.address.lower() == pool_details.token0.address.lower()
            raw_price = get_onchain_price_v3(self._web3, pool_details.address, reverse_token_order=reverse)

            return raw_price

        except Exception as e:
            logger.error(f"Error getting V3 price: {str(e)}")
            return None

    def get_token_price(self, base_token: TokenInfo, quote_token: TokenInfo) -> Optional[Decimal]:
        """Get token price using the appropriate Uniswap version.

        Gets the current price from either Uniswap V2 or V3 pools based on the client version.
        The price is returned in terms of base/quote (how much quote token per base token).

        Args:
            base_token (TokenInfo): Base token info (token being priced)
            quote_token (TokenInfo): Quote token info (denominator token)

        Returns:
            Optional[Decimal]: Current price in base/quote terms, or None if no pool exists
            or there was an error getting the price
            or there was an error getting the price
        """
        try:
            logger.debug(
                f"Getting price for {base_token.symbol}/{quote_token.symbol} on {self.chain} using Uniswap {self.version}"
            )

            if self.version == "v2":
                return self._get_v2_price(base_token=base_token, quote_token=quote_token)
            elif self.version == "v3":
                return self._get_v3_price(base_token=base_token, quote_token=quote_token)
            else:
                raise ValueError(f"Unsupported Uniswap version: {self.version}")

        except Exception as e:
            logger.error(f"Error getting price: {str(e)}")
            return None

    def get_markets_for_tokens(self, tokens: List[TokenInfo]) -> List[Tuple[TokenInfo, TokenInfo]]:
        """Get list of valid trading pairs between the provided tokens.

        Args:
            tokens: List of tokens to find trading pairs between

        Returns:
            List of token pairs (base, quote) that form valid markets
        """
        if self.version == "v2":
            return self._get_v2_markets_for_tokens(tokens)
        elif self.version == "v3":
            return self._get_v3_markets_for_tokens(tokens)
        else:
            raise ValueError(f"Unsupported Uniswap version: {self.version}")

    def _get_v2_markets_for_tokens(self, tokens: List[TokenInfo]) -> List[Tuple[TokenInfo, TokenInfo]]:
        """Get all V2 pairs between the provided tokens."""
        markets = []
        factory = self._web3.eth.contract(
            address=self._web3.to_checksum_address(self._factory), abi=UNISWAP_V2_FACTORY_ABI
        )

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

    def _get_v3_markets_for_tokens(self, tokens: List[TokenInfo]) -> List[Tuple[TokenInfo, TokenInfo]]:
        """Get all V3 pools between the provided tokens."""
        markets = []
        factory = self._web3.eth.contract(
            address=self._web3.to_checksum_address(self._factory), abi=UNISWAP_V3_FACTORY_ABI
        )

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


class UniswapClientV2(UniswapClient):
    def __init__(self, config: Config, chain: str):
        super().__init__(config, chain, "v2")


class UniswapClientV3(UniswapClient):
    def __init__(self, config: Config, chain: str):
        super().__init__(config, chain, "v3")
