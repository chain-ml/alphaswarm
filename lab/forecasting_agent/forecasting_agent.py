from typing import List
import asyncio
import dotenv

from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.agent.clients import TerminalClient
from alphaswarm.tools.alchemy import AlchemyPriceHistoryByAddress, AlchemyPriceHistoryBySymbol
from alphaswarm.tools.cookie.cookie_metrics import CookieMetricsBySymbol
from alphaswarm.config import Config, BASE_PATH
from alphaswarm.utils.file_utils import read_text_file_to_string
from lab.forecasting_agent.price_forecasting_tool import PriceForecastingTool
from smolagents import Tool

async def main() -> None:
    dotenv.load_dotenv()

    tools: List[Tool] = [
        AlchemyPriceHistoryBySymbol(),
        CookieMetricsBySymbol(),
        PriceForecastingTool(),
    ]

    system_prompt = read_text_file_to_string(BASE_PATH / "lab/forecasting_agent/prompts/forecasting_agent_system_prompt.txt")

    specialization = """
    ## Specialization
    You are specialized in making price forecasts for crypto assets.

    When doing this:
    1. Get the historical price data for the token
    2. Use additional tools to get market context that is relevant to predicting the price of a token
    3. Use may use more than one tool to get additional market context if needed and if available
    4. Use the forecasting tool to generate a price forecast
    5. Your final response must include the reasoning behind the forecast
    """

    system_prompt = system_prompt.replace("{{specialization}}", specialization)

    agent = AlphaSwarmAgent(tools=tools, model_id="anthropic/claude-3-5-sonnet-20240620", system_prompt=system_prompt)

    terminal = TerminalClient("AlphaSwarm terminal", agent)
    await asyncio.gather(
        terminal.start(),
    )


if __name__ == "__main__":
    asyncio.run(main())
