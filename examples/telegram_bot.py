import asyncio
import logging
from typing import List

import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.agent.clients.telegram_bot import TelegramBot
from alphaswarm.config import Config
from alphaswarm.tools.alchemy import AlchemyPriceHistoryByAddress, AlchemyPriceHistoryBySymbol
from alphaswarm.tools.exchanges import GetTokenPriceTool
from alphaswarm.tools.price_tool import PriceTool
from alphaswarm.tools.strategy_analysis.generic import GenericStrategyAnalysisTool
from smolagents import Tool

logging.getLogger("smolagents").setLevel(logging.ERROR)


async def main():
    # Initialize the manager with your tools
    dotenv.load_dotenv()
    config = Config()

    tools: List[Tool] = [
        PriceTool(),
        GetTokenPriceTool(config),
        AlchemyPriceHistoryByAddress(),
        AlchemyPriceHistoryBySymbol(),
        GenericStrategyAnalysisTool(),
    ]  # Add your tools here

    agent = AlphaSwarmAgent(tools=tools, model_id="gpt-4o")
    bot_token = config.get("telegram", {}).get("bot_token")
    tg_bot = TelegramBot(bot_token=bot_token, agent=agent)

    await asyncio.gather(
        tg_bot.start(),
    )


if __name__ == "__main__":
    asyncio.run(main())
