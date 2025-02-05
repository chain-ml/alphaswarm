from typing import List
import asyncio
import dotenv

from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.agent.clients import TerminalClient
from alphaswarm.tools.alchemy import AlchemyPriceHistoryByAddress, AlchemyPriceHistoryBySymbol
from alphaswarm.tools.cookie.cookie_metrics import CookieMetricsBySymbol
from alphaswarm.config import Config, BASE_PATH
from lab.forecasting_agent.price_forecasting_tool import PriceForecastingTool
from smolagents import Tool

async def main() -> None:
    dotenv.load_dotenv()


    tools: List[Tool] = [
        AlchemyPriceHistoryBySymbol(),
        CookieMetricsBySymbol(),
        PriceForecastingTool(),
    ]

    hints = """
    ## Tokens
    These are the symbols and addresses of the tokens you are responsible for forecasting.
    - AIXBT (base): 0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825
    - VIRTUAL (base): 0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b
    - VADER (base): 0x731814e491571A2e9eE3c5b1F7f3b962eE8f4870
    """


    agent = AlphaSwarmAgent(tools=tools, model_id="anthropic/claude-3-5-sonnet-20240620", hints=hints)

    terminal = TerminalClient("AlphaSwarm terminal", agent)
    await asyncio.gather(
        terminal.start(),
    )


if __name__ == "__main__":
    asyncio.run(main())
