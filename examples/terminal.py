import asyncio
from typing import List

import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.agent.clients import TerminalClient

# from alphaswarm.config import Config
from alphaswarm.tools.alchemy import AlchemyPriceHistoryByAddress, AlchemyPriceHistoryBySymbol
from alphaswarm.tools.cookie.cookie_metrics import (
    CookieMetricsByContract,
    CookieMetricsBySymbol,
    CookieMetricsByTwitter,
    CookieMetricsPaged,
)
from alphaswarm.tools.strategy_analysis.generic import GenericStrategyAnalysisTool
from smolagents import Tool


async def main():
    # Initialize the manager with your tools
    dotenv.load_dotenv()
    # config = Config()  # Uncomment if tools require config

    tools: List[Tool] = [
        AlchemyPriceHistoryByAddress(),
        AlchemyPriceHistoryBySymbol(),
        GenericStrategyAnalysisTool(),
        CookieMetricsByContract(),
        CookieMetricsBySymbol(),
        CookieMetricsByTwitter(),
        CookieMetricsPaged(),
    ]
    hints = """You are a trading agent that uses a set of tools to analyze the market and make trading decisions.
    You are given a set of tools to analyze the market and make trading decisions.
    You are also given a strategy config that outlines the rules for the trading strategy.
    """
    agent = AlphaSwarmAgent(tools=tools, model_id="anthropic/claude-3-5-sonnet-latest", hints=hints)

    terminal = TerminalClient("AlphaSwarm terminal", agent)
    await asyncio.gather(
        terminal.start(),
    )


if __name__ == "__main__":
    asyncio.run(main())
