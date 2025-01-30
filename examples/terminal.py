import asyncio
from typing import List

import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent, AlphaSwarmAgentManager
from alphaswarm.agent.clients import TerminalClient
from alphaswarm.config import Config
from alphaswarm.tools.alchemy import AlchemyPriceHistoryByAddress, AlchemyPriceHistoryBySymbol
from alphaswarm.tools.exchanges import GetTokenPriceTool
from alphaswarm.tools.price_tool import PriceTool
from smolagents import Tool

# summarize the price history for ETH for the past week
# what is the current price for AIXBT
# how much AIXBT could I buy for 10 USDC?


async def main():
    # Initialize the manager with your tools
    dotenv.load_dotenv()
    config = Config()

    tools: List[Tool] = [
        PriceTool(),
        GetTokenPriceTool(config),
        AlchemyPriceHistoryByAddress(),
        AlchemyPriceHistoryBySymbol(),
    ]
    agent = AlphaSwarmAgent(tools=tools, model_id="gpt-4o")
    manager = AlphaSwarmAgentManager(agent)

    terminal = TerminalClient(manager, "terminal")

    await asyncio.gather(
        terminal.start(),
    )


if __name__ == "__main__":
    asyncio.run(main())
