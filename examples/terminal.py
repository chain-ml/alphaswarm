import asyncio
from typing import List

import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent, AlphaSwarmAgentManager
from alphaswarm.agent.clients import TerminalClient
from alphaswarm.config import Config
from alphaswarm.tools.alchemy import AlchemyPriceHistory
from alphaswarm.tools.exchanges import GetTokenPriceTool
from alphaswarm.tools.price_tool import PriceTool
from smolagents import Tool


async def main():
    # Initialize the manager with your tools
    dotenv.load_dotenv()
    config = Config()

    tools: List[Tool] = [PriceTool(), GetTokenPriceTool(config), AlchemyPriceHistory()]  # Add you
    agent = AlphaSwarmAgent(tools=tools, model_id="gpt-4o")  # r tools here
    manager = AlphaSwarmAgentManager(agent)

    terminal = TerminalClient(manager, "terminal")

    await asyncio.gather(
        terminal.start(),
    )


if __name__ == "__main__":
    asyncio.run(main())
