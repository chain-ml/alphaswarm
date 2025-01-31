import asyncio
from typing import List

import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.agent.clients import TerminalClient
from alphaswarm.config import CONFIG_PATH
from alphaswarm.utils import read_text_file_to_string

# from alphaswarm.config import Config
from alphaswarm.tools.alchemy import AlchemyPriceHistoryByAddress, AlchemyPriceHistoryBySymbol
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
    ]

    # Optional step to provide a custom system prompt.
    # If no custom system prompt is provided, a default one will be used.
    system_prompt = read_text_file_to_string(CONFIG_PATH / "reference_custom_code_agent_system_prompt.txt")
    
    hints = """You are a trading agent that uses a set of tools to analyze the market and make trading decisions.
    You are given a set of tools to analyze the market and make trading decisions.
    You are also given a strategy config that outlines the rules for the trading strategy.
    """
    
    agent = AlphaSwarmAgent(tools=tools, model_id="anthropic/claude-3-5-sonnet-latest", system_prompt=system_prompt, hints=hints)

    terminal = TerminalClient("AlphaSwarm terminal", agent)
    await asyncio.gather(
        terminal.start(),
    )


if __name__ == "__main__":
    asyncio.run(main())
