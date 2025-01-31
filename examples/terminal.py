import asyncio
from typing import List

import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.agent.clients import TerminalClient
from alphaswarm.config import CONFIG_PATH

# from alphaswarm.config import Config
from alphaswarm.tools.alchemy import AlchemyPriceHistoryByAddress, AlchemyPriceHistoryBySymbol
from alphaswarm.tools.strategy_analysis.generic import GenericStrategyAnalysisTool
from alphaswarm.utils import read_text_file_to_string
from smolagents import Tool


async def main():
    # Initialize the manager with your tools
    dotenv.load_dotenv()
    # config = Config()  # Uncomment if tools require config

    tools: List[Tool] = [
        AlchemyPriceHistoryByAddress(),
        AlchemyPriceHistoryBySymbol(),
        GenericStrategyAnalysisTool(),
    ]

    # Optional step to provide a custom system prompt.
    # If no custom system prompt is provided, a default one will be used.
    system_prompt = read_text_file_to_string(CONFIG_PATH / "reference_custom_code_agent_system_prompt.txt")

    hints = """You must only use real data obtained through the available tools - never make up, synthesize, or assume any market data.
    If you don't have access to certain data through the tools, acknowledge the limitation rather than making assumptions.
    """

    agent = AlphaSwarmAgent(
        tools=tools, model_id="anthropic/claude-3-5-sonnet-latest", system_prompt=system_prompt, hints=hints
    )

    terminal = TerminalClient("AlphaSwarm terminal", agent)
    await asyncio.gather(
        terminal.start(),
    )


if __name__ == "__main__":
    asyncio.run(main())
