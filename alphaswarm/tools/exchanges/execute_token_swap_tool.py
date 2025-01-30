import logging
from typing import Optional

from alphaswarm.config import Config
from alphaswarm.services.chains import Web3Client, Web3ClientFactory
from alphaswarm.services.exchanges import DEXFactory
from smolagents import Tool

logger = logging.getLogger(__name__)


class ExecuteTokenSwapTool(Tool):
    """Tool for executing token swaps on supported DEXes."""

    name = "execute_token_swap"
    description = "Execute a token swap on a supported DEX (Uniswap V2/V3 on Ethereum and Base chains)."
    inputs = {
        "token_quote": {
            "type": "string",
            "description": "The quote token symbol (e.g., 'USDC', 'ETH', 'WETH') - the token being sold",
        },
        "token_base": {
            "type": "string",
            "description": "The base token symbol (e.g., 'USDC', 'ETH', 'WETH') - the token being bought",
        },
        "amount": {"type": "number", "description": "The amount of quote token to swap", "required": True},
        "chain": {
            "type": "string",
            "description": "The chain to execute the swap on (e.g., 'ethereum', 'ethereum_sepolia', 'base')",
            "nullable": True,
        },
        "dex_type": {
            "type": "string",
            "description": "The DEX type to use (e.g., 'uniswap_v2', 'uniswap_v3')",
            "nullable": True,
        },
        "slippage_bps": {
            "type": "integer",
            "description": "Maximum slippage in basis points (e.g., 100 = 1%)",
            "nullable": True,
        },
    }
    output_type = "string"

    def __init__(self, config: Config, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.config = config
        # Initialize with None, we'll get the appropriate client when needed
        self.web3_client: Optional[Web3Client] = None

    def _get_web3_client(self, chain: str) -> Web3Client:
        """Get the appropriate Web3Client for the chain"""
        if not self.web3_client:
            self.web3_client = Web3ClientFactory.get_instance().get_client(chain, self.config)
        if not self.web3_client:
            raise RuntimeError(f"Failed to get Web3Client for chain {chain}")
        return self.web3_client

    def forward(
        self,
        token_quote: str,
        token_base: str,
        amount: float,
        chain: str = "ethereum",
        dex_type: str = "uniswap_v3",
        slippage_bps: int = 100,
    ) -> str:
        """Execute a token swap."""
        # Create DEX client
        dex_client = DEXFactory.create(dex_name=dex_type, config=self.config, chain=chain)

        # Get wallet address and private key from chain config
        chain_config = self.config.get_chain_config(chain)

        # Get token info and create TokenInfo objects
        try:
            token_config = chain_config.tokens
            base_token_info = token_config[token_base]
            quote_token_info = token_config[token_quote]
        except KeyError as e:
            return f"Token not found in config: {str(e)}"

        # Log token details
        logger.info(
            f"Swapping {amount} {quote_token_info.symbol} ({quote_token_info.address}) for {base_token_info.symbol} ({base_token_info.address}) on {chain}"
        )

        # Execute swap
        result = dex_client.swap(
            base_token=base_token_info,
            quote_token=quote_token_info,
            quote_amount=amount,
            slippage_bps=slippage_bps,
        )

        if result.success:
            return f"Swap successful! Swapped {result.quote_amount} {quote_token_info.symbol} for {result.base_amount} {base_token_info.symbol}. TX Hash: {result.tx_hash}"

        raise RuntimeError(f"Swap failed: {result.error}")
