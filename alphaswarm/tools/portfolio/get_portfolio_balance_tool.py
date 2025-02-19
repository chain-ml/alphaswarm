from typing import Any, Dict, List, Optional

from alphaswarm.config import Config
from alphaswarm.core.token import TokenAmount
from alphaswarm.services.portfolio import Portfolio
from smolagents import Tool


class GetPortfolioBalanceTool(Tool):
    name = "get_portfolio_balance"
    description = "List all the tokens owned by the user"

    inputs: Dict = {
        "chain": {
            "type": "string",
            "description": "Filter result for that chain if provided. Otherwise, execute for all chains",
            "enum": ["solana", "base", "ethereum", "ethereum_sepolia"],
            "nullable": True,
        }
    }
    output_type = "object"

    def __init__(self, config: Config, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._portfolio = Portfolio.from_config(config)

    def forward(self, chain: Optional[str]) -> List[TokenAmount]:
        return self._portfolio.get_token_balances(chain)
