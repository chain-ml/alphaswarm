from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Self, Tuple, Union

from alphaswarm.config import ChainConfig, Config, TokenInfo, UniswapV3Settings
from alphaswarm.services.chains.evm import ZERO_ADDRESS, EVMClient, EVMContract, EVMSigner
from alphaswarm.services.exchanges.base import Slippage, TokenPrice
from alphaswarm.services.exchanges.uniswap.constants_v3 import (
    UNISWAP_V3_DEPLOYMENTS,
    UNISWAP_V3_FACTORY_ABI,
    UNISWAP_V3_ROUTER2_ABI,
    UNISWAP_V3_ROUTER_ABI,
    UNISWAP_V3_VERSION,
)
from alphaswarm.services.exchanges.uniswap.uniswap_client_base import UniswapClientBase
from eth_defi.uniswap_v3.pool import PoolDetails, fetch_pool_details
from eth_defi.uniswap_v3.price import get_onchain_price
from eth_typing import ChecksumAddress, HexAddress
from pydantic import BaseModel, Field
from typing_extensions import Annotated
from web3.types import TxReceipt

logger = logging.getLogger(__name__)


class FactoryContract(EVMContract):
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
    def __init__(self, client: EVMClient, address: HexAddress) -> None:
        self._client = client
        self._address = address
        self._cached_pool_details: Optional[PoolDetails] = None
        self._liquidity: Optional[int] = None

    @property
    def _pool_details(self) -> PoolDetails:
        if self._cached_pool_details is None:
            self._cached_pool_details = fetch_pool_details(self._client.client, self._address)
        return self._cached_pool_details

    @property
    def address(self) -> ChecksumAddress:
        return EVMClient.to_checksum_address(self._address)

    @property
    def raw_fee(self) -> int:
        return self._pool_details.raw_fee

    @property
    def liquidity(self) -> int:
        if self._liquidity is None:
            self._liquidity = self._pool_details.pool.functions.liquidity().call()
        return self._liquidity

    def get_price_for_token_out(self, token_out: ChecksumAddress) -> Decimal:
        """Get the current mid-price for the pair of token.

        Args:
            token_out: The token to be bought (going out of the pool)

        Returns:
            Decimal: the amount of token_out (bought) for exactly one token_in (sold)
        """

        reverse = token_out.lower() == self._pool_details.token0.address.lower()
        return get_onchain_price(self._client.client, self._address, reverse_token_order=reverse)

    def get_price_for_token_in(self, token_in: ChecksumAddress) -> Decimal:
        """Get the current mid-price for the pair of token.

        Args:
            token_in: The token to be bought (going into the pool)

        Returns:
            Decimal: the amount of token_in (sold) for exactly one token_out (bought)
        """

        reverse = token_in.lower() == self._pool_details.token1.address.lower()
        return get_onchain_price(self._client.client, self._address, reverse_token_order=reverse)


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


class RouterContract(EVMContract):
    def __init__(self, client: EVMClient, address: ChecksumAddress, abi: List[Dict]) -> None:
        super().__init__(client, address, abi)

    @classmethod
    def from_chain(cls, client: EVMClient, address: ChecksumAddress, chain: str) -> Self:
        router_abi = UNISWAP_V3_ROUTER2_ABI if chain in ["base", "ethereum_sepolia"] else UNISWAP_V3_ROUTER_ABI
        return cls(client, address, router_abi)

    def exact_input_single(self, signer: EVMSigner, params: ExactInputSingleParams) -> TxReceipt:
        return self._client.process(self._contract.functions.exactInputSingle(params.to_dict()), signer)


class UniswapClientV3(UniswapClientBase):
    def __init__(self, chain_config: ChainConfig, settings: UniswapV3Settings) -> None:
        super().__init__(chain_config=chain_config, version=UNISWAP_V3_VERSION)
        self._factory_contract: Optional[FactoryContract] = None
        self._settings = settings

    @property
    def factory_contract(self) -> FactoryContract:
        if self._factory_contract is None:
            self._factory_contract = FactoryContract(self._evm_client, self._factory)
        return self._factory_contract

    def _get_router(self) -> ChecksumAddress:
        return self._evm_client.to_checksum_address(UNISWAP_V3_DEPLOYMENTS[self.chain]["router"])

    def _get_factory(self) -> ChecksumAddress:
        return self._evm_client.to_checksum_address(UNISWAP_V3_DEPLOYMENTS[self.chain]["factory"])

    def _swap(
        self, token_out: TokenInfo, token_in: TokenInfo, address: str, wei_in: int, slippage_bps: int
    ) -> List[TxReceipt]:
        """Execute a swap on Uniswap V3."""
        # Handle token approval and get fresh nonce
        approval_receipt = self._approve_token_spending(token_in, wei_in)

        # Build a swap transaction
        pool = self._get_pool(token_out, token_in)
        logger.info(f"Using Uniswap V3 pool at address: {pool.address} (raw fee tier: {pool.raw_fee})")

        # Get the on-chain price from the pool and reverse if necessary
        price = self._get_token_price_from_pool(token_out, pool)
        logger.info(f"Pool raw price: {price} ({token_out.symbol} per {token_in.symbol})")

        # Convert to decimal for calculations
        amount_in_decimal = token_in.convert_from_wei(wei_in)
        logger.info(f"Actual input amount: {amount_in_decimal} {token_in.symbol}")

        # Calculate expected output
        expected_output_decimal = amount_in_decimal * price
        logger.info(f"Expected output: {expected_output_decimal} {token_out.symbol}")

        # Convert expected output to raw integer
        raw_output = token_out.convert_to_wei(expected_output_decimal)
        logger.info(f"Expected output amount (raw): {raw_output}")

        # Calculate price impact
        pool_liquidity = pool.liquidity
        logger.info(f"Pool liquidity: {pool_liquidity}")

        # Estimate price impact (simplified)
        price_impact = (wei_in * Slippage.base_point) / pool_liquidity  # in bps
        logger.info(f"Estimated price impact: {price_impact:.2f} bps")

        # Check if price impact is too high relative to slippage
        slippage = Slippage(slippage_bps)
        # Price impact should be significantly lower than slippage to leave room for market moves
        if price_impact > (slippage_bps * 0.67):  # If price impact is more than 2/3 of slippage
            logger.warning(
                f"WARNING: Price impact ({price_impact:.2f} bps) is more than 2/3 of slippage tolerance ({slippage})"
            )
            logger.warning(
                "This leaves little room for market price changes between transaction submission and execution"
            )

        # Apply slippage
        min_output_raw = slippage.calculate_minimum_amount(raw_output)
        logger.info(f"Minimum output with {slippage} slippage (raw): {min_output_raw}")

        # Build swap parameters for `exactInputSingle`
        params = ExactInputSingleParams(
            token_in=token_in.checksum_address,
            token_out=token_out.checksum_address,
            fee=pool.raw_fee,
            recipient=self._evm_client.to_checksum_address(address),
            deadline=int(self._evm_client.get_block_latest()["timestamp"] + 300),
            amount_in=wei_in,
            amount_out_minimum=min_output_raw,
            sqrt_price_limit_x96=0,
        )

        # Build swap transaction with EIP-1559 parameters
        router_contract = RouterContract.from_chain(self._evm_client, self._router, self.chain)
        swap_receipt = router_contract.exact_input_single(self.get_signer(), params)

        return [approval_receipt, swap_receipt]

    def _get_token_price(self, token_out: TokenInfo, token_in: TokenInfo) -> TokenPrice:
        pool = self._get_pool(token_out, token_in)
        price = self._get_token_price_from_pool(token_out, pool)
        return TokenPrice(price=price, pool=pool.address)

    @staticmethod
    def _get_token_price_from_pool(token_out: TokenInfo, pool: PoolContract) -> Decimal:
        return pool.get_price_for_token_out(token_out.checksum_address)

    def _get_pool_by_address(self, address: Union[str, HexAddress]) -> PoolContract:
        return PoolContract(self._evm_client, EVMClient.to_checksum_address(address))

    def _get_pool(self, token0: TokenInfo, token1: TokenInfo) -> PoolContract:
        """Find the Uniswap V3 pool with highest liquidity for a token pair.

        Checks all configured fee tiers and returns the pool with the highest liquidity.
        The pool details include addresses, tokens, and fee information.

        Args:
            token0: first token of the pair
            token1: second token of the pair

        Returns:
            PoolContract: The pool with the highest liquidity, or None if no pool exists
            or there was an error finding a pool
        """
        max_liquidity = 0
        best_pool = None

        # Check all fee tiers to find pool with highest liquidity
        for fee in self._settings.fee_tiers:
            try:
                pool_address = self.factory_contract.get_pool_address_or_none(
                    token0.checksum_address, token1.checksum_address, fee
                )
                if pool_address is None:
                    continue

                pool = self._get_pool_by_address(pool_address)
                if pool.liquidity > max_liquidity:
                    best_pool = pool
                    max_liquidity = pool.liquidity

            except Exception:
                logger.exception(f"Failed to get pool for fee tier {fee}")
                continue

        if best_pool:
            logger.info(f"Selected pool with highest liquidity: {best_pool.address} (liquidity: {best_pool.liquidity})")
            return best_pool

        logger.warning(f"No V3 pool found for {token0.symbol}/{token1.symbol}")
        raise RuntimeError(f"No pool found for {token0.symbol}/{token1.symbol}")

    def _get_markets_for_tokens(self, tokens: List[TokenInfo]) -> List[Tuple[TokenInfo, TokenInfo]]:
        """Get all V3 pools between the provided tokens."""
        markets = []

        # Get fee tiers from settings
        fee_tiers = self._settings.fee_tiers

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

    @classmethod
    def from_config(cls, config: Config, chain: str) -> UniswapClientV3:
        chain_config = config.get_chain_config(chain)
        return cls(chain_config, config.get_venue_settings_uniswap_v3())
