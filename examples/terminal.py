import asyncio
import os
from typing import List

import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent, AlphaSwarmAgentManager
from alphaswarm.agent.clients import TerminalClient
from alphaswarm.config import Config
from alphaswarm.tools.alchemy import AlchemyPriceHistoryByAddress, AlchemyPriceHistoryBySymbol
from alphaswarm.tools.exchanges import GetTokenPriceTool
from alphaswarm.tools.price_tool import PriceTool
from alphaswarm.utils import read_text_file_to_string
from alphaswarm.config import CONFIG_PATH
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
    ]

    # Optional step to provide a custom system prompt.
    # If no custom system prompt is provided, a default one will be used.
    system_prompt = read_text_file_to_string(CONFIG_PATH / "reference_custom_code_agent_system_prompt.txt")

    agent = AlphaSwarmAgent(tools=tools, model_id="gpt-4o", system_prompt=system_prompt)
    manager = AlphaSwarmAgentManager(agent)

    terminal = TerminalClient(manager, "terminal")

    await asyncio.gather(
        terminal.start(),
    )


if __name__ == "__main__":
    asyncio.run(main())
