import asyncio
import logging
from typing import List

import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.agent.clients.telegram_bot import TelegramBot
from alphaswarm.config import Config
from alphaswarm.core.tool import AlphaSwarmToolBase
from alphaswarm.tools.alchemy import GetAlchemyPriceHistoryByAddress, GetAlchemyPriceHistoryBySymbol
from alphaswarm.tools.cookie import (
    GetCookieMetricsByContract,
    GetCookieMetricsBySymbol,
    GetCookieMetricsByTwitter,
    GetCookieMetricsPaged,
)
from alphaswarm.tools.core import GetTokenAddress, GetUsdPrice
from alphaswarm.tools.exchanges import ExecuteTokenSwap, GetTokenPrice

logging.getLogger("smolagents").setLevel(logging.ERROR)


async def main() -> None:
    dotenv.load_dotenv()
    config = Config()

    tools: List[AlphaSwarmToolBase] = [
        GetUsdPrice(),
        GetTokenAddress(config),
        GetTokenPrice(config),
        GetAlchemyPriceHistoryByAddress(),
        GetAlchemyPriceHistoryBySymbol(),
        GetCookieMetricsByContract(),
        GetCookieMetricsBySymbol(),
        GetCookieMetricsByTwitter(),
        GetCookieMetricsPaged(),
        ExecuteTokenSwap(config),
    ]  # Add your tools here

    llm_config = config.get_default_llm_config("anthropic")
    agent = AlphaSwarmAgent(tools=tools, model_id=llm_config.model_id)
    bot_token = config.get("telegram", {}).get("bot_token")
    tg_bot = TelegramBot(bot_token=bot_token, agent=agent)

    await asyncio.gather(
        tg_bot.start(),
    )


if __name__ == "__main__":
    asyncio.run(main())
