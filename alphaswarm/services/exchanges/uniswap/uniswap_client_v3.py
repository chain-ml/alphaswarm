import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Self, Tuple, Union

from alphaswarm.config import Config, TokenInfo
from alphaswarm.services.chains.evm import ZERO_ADDRESS, EMVContract, EVMClient, EVMSigner
from alphaswarm.services.exchanges.uniswap.constants_v3 import (
    UNISWAP_V3_DEPLOYMENTS,
    UNISWAP_V3_FACTORY_ABI,
    UNISWAP_V3_ROUTER2_ABI,
    UNISWAP_V3_ROUTER_ABI,
)
from alphaswarm.services.exchanges.uniswap.uniswap_client_base import UniswapClientBase
from eth_defi.uniswap_v3.pool import PoolDetails, fetch_pool_details
from eth_defi.uniswap_v3.price import get_onchain_price
from eth_typing import ChecksumAddress, HexAddress
from pydantic import BaseModel, Field
from typing_extensions import Annotated
from web3 import Web3
from web3.types import TxReceipt

logger = logging.getLogger(__name__)


class FactoryContract(EMVContract):
    def __init__(self, client: EVMClient, address: ChecksumAddress) -> None:
        super().__init__(client, address, UNISWAP_V3_FACTORY_ABI)

    def get_pool_address_or_none(
        self, token0: ChecksumAddress, token1: ChecksumAddress, fee: int
    ) -> Optional[ChecksumAddress]:
        result = self._contract.functions.getPool(token0, token1, fee).call()
        if result == ZERO_ADDRESS:
            return None
        return ChecksumAddress(result)


class PoolContract:
    def __init__(self, client: Web3, address: HexAddress) -> None:
        self._client = client
        self._address = address
        self._pool_details: Optional[PoolDetails] = None
        self._liquidity: Optional[int] = None

    @property
    def pool_details(self) -> PoolDetails:
        if self._pool_details is None:
            self._pool_details = fetch_pool_details(self._client, self._address)
        return self._pool_details

    @property
    def liquidity(self) -> int:
        if self._liquidity is None:
            self._liquidity = self.pool_details.pool.functions.liquidity().call()
        return self._liquidity

    @classmethod
    def from_pool_details(cls, pool_details: PoolDetails) -> Self:
        result = cls(pool_details.pool.w3, pool_details.address)
        result._pool_details = pool_details
        return result


class ExactInputSingleParams(BaseModel):
    token_in: Annotated[ChecksumAddress, Field(serialization_alias="tokenIn")]
    token_out: Annotated[ChecksumAddress, Field(serialization_alias="tokenOut")]
    fee: int
    recipient: ChecksumAddress
    deadline: int
    amount_in: Annotated[int, Field(serialization_alias="amountIn")]
    amount_out_minimum: Annotated[int, Field(serialization_alias="amountOutMinimum")]
    sqrt_price_limit_x96: Annotated[int, Field(serialization_alias="sqrtPriceLimitX96")]

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(by_alias=True)


class RouterContract(EMVContract):
    def __init__(self, client: EVMClient, address: ChecksumAddress, abi: List[Dict]) -> None:
        super().__init__(client, address, abi)

    @classmethod
    def from_chain(cls, client: EVMClient, address: ChecksumAddress, chain: str) -> Self:
        router_abi = UNISWAP_V3_ROUTER2_ABI if chain in ["base", "ethereum_sepolia"] else UNISWAP_V3_ROUTER_ABI
        return cls(client, address, router_abi)

    def exact_input_single(self, signer: EVMSigner, params: ExactInputSingleParams) -> TxReceipt:
        return self._client.process(self._contract.functions.exactInputSingle(params.to_dict()), signer)


class UniswapClientV3(UniswapClientBase):
    def __init__(self, config: Config, chain: str):
        super().__init__(config, chain, "v3")
        self._factory_contract: Optional[FactoryContract] = None

    @property
    def factory_contract(self) -> FactoryContract:
        if self._factory_contract is None:
            self._factory_contract = FactoryContract(self._evm_client, self._factory)
        return self._factory_contract

    def _get_router(self, chain: str) -> ChecksumAddress:
        return self._evm_client.to_checksum_address(UNISWAP_V3_DEPLOYMENTS[chain]["router"])

    def _get_factory(self, chain: str) -> ChecksumAddress:
        return self._evm_client.to_checksum_address(UNISWAP_V3_DEPLOYMENTS[chain]["factory"])

    def _swap(
        self, base: TokenInfo, quote: TokenInfo, address: str, quote_wei: int, slippage_bps: int
    ) -> List[TxReceipt]:
        """Execute a swap on Uniswap V3."""
        # Handle token approval and get fresh nonce
        approval_receipt = self._approve_token_spend(quote, quote_wei)

        # Build a swap transaction
        pool_details = self._get_pool(base, quote)
        logger.info(f"Using Uniswap V3 pool at address: {pool_details.address} (raw fee tier: {pool_details.raw_fee})")

        # Get the on-chain price from the pool and reverse if necessary
        price = self._get_token_price_from_pool(quote, pool_details)
        logger.info(f"Pool raw price: {price} ({quote.symbol} per {base.symbol})")

        # Convert to decimal for calculations
        input_amount_decimal = quote.convert_from_wei(quote_wei)
        logger.info(f"Actual input amount: {input_amount_decimal} {quote.symbol}")

        # Calculate expected output
        expected_output_decimal = input_amount_decimal / price
        logger.info(f"Expected output: {expected_output_decimal} {base.symbol}")

        # Convert expected output to raw integer
        raw_output = base.convert_to_wei(expected_output_decimal)
        logger.info(f"Expected output amount (raw): {raw_output}")

        # Calculate price impact
        pool_liquidity = PoolContract.from_pool_details(pool_details).liquidity
        logger.info(f"Pool liquidity: {pool_liquidity}")

        # Estimate price impact (simplified)
        price_impact = (quote_wei * 10000) / pool_liquidity  # in bps
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
        slippage_multiplier = Decimal(1) - (Decimal(slippage_bps) / Decimal(10000))
        min_output_raw = int(raw_output * slippage_multiplier)
        logger.info(f"Minimum output with {slippage_bps} bps slippage (raw): {min_output_raw}")

        # Build swap parameters for `exactInputSingle`
        params = ExactInputSingleParams(
            token_in=quote.checksum_address,
            token_out=base.checksum_address,
            fee=pool_details.raw_fee,
            recipient=self._evm_client.to_checksum_address(address),
            deadline=int(self._web3.eth.get_block("latest")["timestamp"] + 300),
            amount_in=quote_wei,
            amount_out_minimum=min_output_raw,
            sqrt_price_limit_x96=0,
        )

        # Build swap transaction with EIP-1559 parameters
        router_contract = RouterContract.from_chain(self._evm_client, self._router, self.chain)
        swap_receipt = router_contract.exact_input_single(self.get_signer(), params)

        return [approval_receipt, swap_receipt]

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
        """
        pool_details = self._get_pool(base_token, quote_token)
        return self._get_token_price_from_pool(quote_token, pool_details)

    def _get_token_price_from_pool(self, quote_token: TokenInfo, pool_details: PoolDetails) -> Decimal:
        reverse = quote_token.address.lower() == pool_details.token0.address.lower()
        raw_price = get_onchain_price(self._web3, pool_details.address, reverse_token_order=reverse)
        return raw_price

    def _get_pool_by_address(self, address: Union[str, HexAddress]):
        return PoolContract(self._web3, self._web3.to_checksum_address(address))

    def _get_pool(self, token0: TokenInfo, token1: TokenInfo) -> PoolDetails:
        """Find the Uniswap V3 pool with highest liquidity for a token pair.

        Checks all configured fee tiers and returns the pool with the highest liquidity.
        The pool details include addresses, tokens, and fee information.

        Args:
            token0: first token of the pair
            token1: second token of the pair

        Returns:
            PoolDetails: Details about the pool with highest liquidity, or None if no pool exists
            or there was an error finding a pool
        """
        settings = self.config.get_venue_settings_uniswap_v3()

        max_liquidity = 0
        best_pool_details = None

        # Check all fee tiers to find pool with highest liquidity
        for fee in settings.fee_tiers:
            try:
                pool_address = self.factory_contract.get_pool_address_or_none(
                    token0.checksum_address, token1.checksum_address, fee
                )
                if pool_address is None:
                    continue

                pool = PoolContract(self._web3, pool_address)
                if pool.liquidity > max_liquidity:
                    best_pool_details = pool
                    max_liquidity = pool.liquidity

            except Exception:
                logger.exception(f"Failed to get pool for fee tier {fee}")
                continue

        if best_pool_details:
            logger.info(
                f"Selected pool with highest liquidity: {best_pool_details.pool_details.address} (liquidity: {best_pool_details.liquidity})"
            )
            return best_pool_details.pool_details

        logger.warning(f"No V3 pool found for {token0.symbol}/{token1.symbol}")
        raise RuntimeError(f"No pool found for {token0.symbol}/{token1.symbol}")

    def _get_markets_for_tokens(self, tokens: List[TokenInfo]) -> List[Tuple[TokenInfo, TokenInfo]]:
        """Get all V3 pools between the provided tokens."""
        markets = []

        # Get fee tiers from settings
        settings = self.config.get_venue_settings_uniswap_v3()
        fee_tiers = settings.fee_tiers

        # Check each possible token pair
        for i, token1 in enumerate(tokens):
            for token2 in tokens[i + 1 :]:  # Only check each pair once
                try:
                    # Check each fee tier
                    for fee in fee_tiers:
                        pool_address = self.factory_contract.get_pool_address_or_none(
                            token1.checksum_address, token2.checksum_address, fee
                        )
                        if pool_address is None:
                            continue
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
