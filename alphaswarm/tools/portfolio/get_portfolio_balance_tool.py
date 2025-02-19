from typing import Any, Dict, List

from alphaswarm.config import Config
from alphaswarm.core.token import TokenAmount
from alphaswarm.services.portfolio.portfolio import Portfolio
from smolagents import Tool


class GetPortfolioBalanceTool(Tool):
    name = "get_portfolio_balance"
    description = "List all the tokens owned by the user"

    inputs: Dict = {}
    output_type = "object"

    def __init__(self, config: Config, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._portfolio = Portfolio.from_config(config)

    def forward(self) -> List[TokenAmount]:
        return self._portfolio.get_token_balances()
