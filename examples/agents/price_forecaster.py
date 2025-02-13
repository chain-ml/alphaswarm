import asyncio
from typing import List

import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.agent.clients import TerminalClient
from alphaswarm.tools.alchemy import AlchemyPriceHistoryBySymbol
from alphaswarm.tools.cookie.cookie_metrics import CookieMetricsBySymbol, CookieMetricsPaged
from alphaswarm.tools.forecasting.price_forecasting_tool import PriceForecastingTool
from smolagents import Tool


class ForecastingAgent(AlphaSwarmAgent):
    def __init__(self) -> None:
        tools: List[Tool] = [
            AlchemyPriceHistoryBySymbol(),
            CookieMetricsBySymbol(),
            CookieMetricsPaged(),
            PriceForecastingTool(),
        ]

        hints = """P.S. Here are some hints to help you succeed:
        - Use the `AlchemyPriceHistoryBySymbol` tool to get the historical price data for the token
        - Use the `CookieMetricsBySymbol` tool to get metrics about the subject token
        - Use the `CookieMetricsPaged` tool to get a broader market overview of related AI agent tokens
        - Use the `PriceForecastingTool` once you have gathered the necessary data to produce a forecast
        - Please respond with the output of the `PriceForecastingTool` directly -- we don't need to reformat it.
        """

        super().__init__(tools=tools, model_id="anthropic/claude-3-5-sonnet-20241022", hints=hints)


async def main() -> None:
    dotenv.load_dotenv()

    agent = ForecastingAgent()

    terminal = TerminalClient("AlphaSwarm terminal", agent)
    await asyncio.gather(
        terminal.start(),
    )


if __name__ == "__main__":
    asyncio.run(main())
