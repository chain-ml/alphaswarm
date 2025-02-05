import logging
from abc import abstractmethod
from decimal import Decimal
from typing import List, Tuple

from alphaswarm.config import Config, TokenInfo
from alphaswarm.services.chains.evm import ERC20Contract, EVMClient, EVMSigner
from alphaswarm.services.exchanges.base import DEXClient, SwapResult
from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress, HexAddress
from web3.types import TxReceipt

# Set up logger
logger = logging.getLogger(__name__)


class UniswapClientBase(DEXClient):
    def __init__(self, config: Config, chain: str, version: str) -> None:
        super().__init__(config, chain)
        self.version = version
        self._router = self._get_router(self.chain)
        self._factory = self._get_factory(self.chain)
        self._evm_client = EVMClient(self.config, self.chain)
        self._web3 = self._evm_client.client

        logger.info(f"Created {self.__class__.__name__} instance for chain {self.chain}")

    @property
    def evm_client(self) -> EVMClient:
        return self._evm_client

    # TODO this would need to become an input parameter for relevant functions
    def get_signer(self) -> EVMSigner:
        return EVMSigner(self.chain_config.private_key)

    @abstractmethod
    def _get_router(self, chain: str) -> ChecksumAddress:
        pass

    @abstractmethod
    def _get_factory(self, chain: str) -> ChecksumAddress:
        pass

    @abstractmethod
    def _swap(
        self, base: TokenInfo, quote: TokenInfo, address: str, quote_wei: int, slippage_bps: int
    ) -> List[TxReceipt]:
        pass

    @abstractmethod
    def _get_token_price(self, base_token: TokenInfo, quote_token: TokenInfo) -> Decimal:
        pass

    @abstractmethod
    def _get_markets_for_tokens(self, tokens: List[TokenInfo]) -> List[Tuple[TokenInfo, TokenInfo]]:
        pass

    @staticmethod
    def _get_final_swap_amount_received(
        swap_receipt: TxReceipt, token_address: HexAddress, user_address: str, token_decimals: int
    ) -> Decimal:
        """Calculate the final amount of tokens received from a swap by parsing Transfer events.

        Looks through the transaction receipt logs for Transfer events where the recipient matches
        the user's address and sums up the transferred amounts.

        Args:
            swap_receipt (dict): The transaction receipt from the swap
            token_address (HexAddress): Hexed Address of the token to track transfers for
            user_address (str): Address of the user receiving the tokens
            token_decimals (int): Number of decimals for the token

        Returns:
            Decimal: Total amount of tokens received, normalized by token decimals
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
        return Decimal(total_received) / (10**token_decimals)

    def swap(
        self,
        base_token: TokenInfo,
        quote_token: TokenInfo,
        quote_amount: Decimal,
        slippage_bps: int = 100,
    ) -> SwapResult:
        """Execute a token swap on Uniswap.

        Args:
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
        logger.info(f"Initiating token swap for {quote_token.symbol} to {base_token.symbol}")

        # Set up account
        account: LocalAccount = Account.from_key(private_key)
        wallet_address = account.address
        logger.info(f"Wallet address: {wallet_address}")

        # Create contract instances
        base_contract = ERC20Contract(self._evm_client, base_token.checksum_address)
        quote_contract = ERC20Contract(self._evm_client, quote_token.checksum_address)

        # Gas balance
        gas_balance = self._evm_client.get_native_balance(account.address)

        # Log balances
        base_balance = base_token.convert_from_wei(base_contract.get_balance(wallet_address))
        quote_balance = quote_token.convert_from_wei(quote_contract.get_balance(wallet_address))
        eth_balance = Decimal(gas_balance) / (10**18)

        logger.info(f"Balance of {base_token.symbol}: {base_balance:,.8f}")
        logger.info(f"Balance of {quote_token.symbol}: {quote_balance:,.8f}")
        logger.info(f"ETH balance for gas: {eth_balance:,.6f}")
        quote_wei = quote_token.convert_to_wei(quote_amount)

        assert quote_balance > 0, f"Cannot perform swap, as you have zero {quote_token.symbol} needed to swap"

        # Each DEX trade is two transactions
        # 1) ERC-20.approve()
        # 2) swap (various functions)

        receipts = self._swap(base_token, quote_token, wallet_address, quote_wei, slippage_bps)

        # Get the actual amount of base token received from the swap receipt
        swap_receipt = receipts[1]
        base_amount = self._get_final_swap_amount_received(
            swap_receipt, base_token.checksum_address, wallet_address, base_token.decimals
        )

        return SwapResult.build_success(
            base_amount=base_amount,
            quote_amount=quote_amount,
            tx_hash=swap_receipt["transactionHash"],  # Return the swap tx hash, not the approve tx
        )

    def _approve_token_spend(self, quote: TokenInfo, raw_amount: int) -> TxReceipt:
        """Handle token approval and return fresh nonce and approval receipt.

        Args:
            quote: Quote token info
            raw_amount: Raw amount to approve

        Returns:
            TxReceipt: approval_receipt

        Raises:
            ValueError: If approval transaction fails
        """
        quote_contract = ERC20Contract(self._evm_client, quote.checksum_address)
        tx_receipt = quote_contract.approve(self.get_signer(), self._router, raw_amount)
        return tx_receipt

    def get_token_price(self, base_token: TokenInfo, quote_token: TokenInfo) -> Decimal:
        """Get token price using the appropriate Uniswap version.

        Gets the current price from either Uniswap V2 or V3 pools based on the client version.
        The price is returned in terms of base/quote (how much quote token per base token).

        Args:
            base_token (TokenInfo): Base token info (token being priced)
            quote_token (TokenInfo): Quote token info (denominator token)

        Returns:
            Decimal: Current price in base/quote terms
        """
        logger.debug(
            f"Getting price for {base_token.symbol}/{quote_token.symbol} on {self.chain} using Uniswap {self.version}"
        )

        return self._get_token_price(base_token=base_token, quote_token=quote_token)

    def get_markets_for_tokens(self, tokens: List[TokenInfo]) -> List[Tuple[TokenInfo, TokenInfo]]:
        """Get list of valid trading pairs between the provided tokens.

        Args:
            tokens: List of tokens to find trading pairs between

        Returns:
            List of token pairs (base, quote) that form valid markets
        """
        return self._get_markets_for_tokens(tokens)
