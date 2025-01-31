import asyncio
from typing import List

import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.agent.clients import TerminalClient
from alphaswarm.config import Config
from alphaswarm.tools.alchemy import AlchemyPriceHistoryByAddress, AlchemyPriceHistoryBySymbol
from alphaswarm.tools.cookie.cookie_metrics import CookieMetricsByContract, CookieMetricsBySymbol, CookieMetricsByTwitter, CookieMetricsPaged
from alphaswarm.tools.exchanges import GetTokenPriceTool
from alphaswarm.tools.price_tool import PriceTool
from smolagents import Tool


async def main():
    # Initialize the manager with your tools
    dotenv.load_dotenv()
    config = Config()

    tools: List[Tool] = [
        PriceTool(),
        GetTokenPriceTool(config),
        AlchemyPriceHistoryByAddress(),
        AlchemyPriceHistoryBySymbol(),
        CookieMetricsByTwitter(),
        CookieMetricsByContract(),
        CookieMetricsPaged(),
        CookieMetricsBySymbol(),
    ]
    agent = AlphaSwarmAgent(tools=tools, model_id="gpt-4o")

    terminal = TerminalClient("AlphaSwarm terminal", agent)
    await asyncio.gather(
        terminal.start(),
    )


if __name__ == "__main__":
    asyncio.run(main())
