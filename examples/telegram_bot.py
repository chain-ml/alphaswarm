import asyncio
import logging
from typing import List

import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.agent.clients.telegram_bot import TelegramBot
from alphaswarm.config import Config
from alphaswarm.tools.alchemy import AlchemyPriceHistoryByAddress, AlchemyPriceHistoryBySymbol
from alphaswarm.tools.exchanges import GetTokenPriceTool
from alphaswarm.tools import GetTokenAddress
from alphaswarm.tools.price_tool import PriceTool
from smolagents import Tool
from alphaswarm.tools.cookie.cookie_metrics import (
    CookieMetricsByContract,
    CookieMetricsBySymbol,
    CookieMetricsByTwitter,
    CookieMetricsPaged,
)
from alphaswarm.tools.exchanges import ExecuteTokenSwapTool

logging.getLogger("smolagents").setLevel(logging.ERROR)


async def main() -> None:
    dotenv.load_dotenv()
    config = Config()

    tools: List[Tool] = [
        PriceTool(),
        GetTokenAddress(config),
        GetTokenPriceTool(config),
        AlchemyPriceHistoryByAddress(),
        AlchemyPriceHistoryBySymbol(),
        CookieMetricsByContract(),
        CookieMetricsBySymbol(),
        CookieMetricsByTwitter(),
        CookieMetricsPaged(),
        ExecuteTokenSwapTool(config),
    ]  # Add your tools here

    agent = AlphaSwarmAgent(tools=tools)
    bot_token = config.get("telegram", {}).get("bot_token")
    tg_bot = TelegramBot(bot_token=bot_token, agent=agent)

    await asyncio.gather(
        tg_bot.start(),
    )


if __name__ == "__main__":
    asyncio.run(main())
