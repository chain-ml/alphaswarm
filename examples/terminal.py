import asyncio
from typing import List

import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.agent.clients import TerminalClient
from alphaswarm.config import Config
from alphaswarm.tools.alchemy import AlchemyPriceHistoryByAddress, AlchemyPriceHistoryBySymbol
from alphaswarm.tools.exchanges import GetTokenPriceTool
from alphaswarm.tools.price_tool import PriceTool
from alphaswarm.tools.strategy_analysis.generic import GenericStrategyAnalysisTool
from alphaswarm.tools.telegram import SendTelegramNotificationTool
from smolagents import Tool


async def main() -> None:
    dotenv.load_dotenv()
    config = Config()

    telegram_config = config.get("telegram", {})
    telegram_bot_token = telegram_config.get("bot_token")
    chat_id = int(telegram_config.get("chat_id"))

    tools: List[Tool] = [
        PriceTool(),
        GetTokenPriceTool(config),
        AlchemyPriceHistoryByAddress(),
        AlchemyPriceHistoryBySymbol(),
        GenericStrategyAnalysisTool(),
        SendTelegramNotificationTool(telegram_bot_token=telegram_bot_token, chat_id=chat_id),
    ]  # Add your tools here
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
