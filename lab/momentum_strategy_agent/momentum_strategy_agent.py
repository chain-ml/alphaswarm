import asyncio
import json
from typing import List

import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.agent.clients import TerminalClient
from alphaswarm.config import BASE_PATH, Config
from alphaswarm.tools.telegram import SendTelegramNotificationTool
from lab.momentum_strategy_agent.price_change_tool import TokenPriceChangeCalculator
from smolagents import Tool


async def main() -> None:
    dotenv.load_dotenv()
    config = Config()

    telegram_config = config.get("telegram", {})
    telegram_bot_token = telegram_config.get("bot_token")
    chat_id = int(telegram_config.get("chat_id"))

    tools: List[Tool] = [
        # PriceTool(),
        # GetTokenPriceTool(config),
        # AlchemyPriceHistoryByAddress(),
        # AlchemyPriceHistoryBySymbol(),
        TokenPriceChangeCalculator(),
        SendTelegramNotificationTool(telegram_bot_token=telegram_bot_token, chat_id=chat_id),
    ]  # Add your tools here

    my_tokens = {
        "AIXBT (base)": "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825",
        "VIRTUAL (base)": "0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b",
        "VADER (base)": "0x731814e491571A2e9eE3c5b1F7f3b962eE8f4870",
        # "AI16Z": "HeLp6NuQkmYB4pYWo2zYs22mESHXPQYzXbB8n4V98jwC",
        # "GRIFFAIN": "8x5VqbHA8D7NkD52uNuS5nnt3PwA8pLD34ymskeSo2Wn",
    }

    specialization = """
    ## Strategy Analysis

    When applicable, you are responsible for analyzing trading strategies against token data.

    When doing this:
    1. Analyze the provided data against the strategy rules (below)
    2. Identify which rules are triggered for which tokens
    3. Provide supporting evidence and context for each alert
    4. Create a brief summary of your overall findings

    For each triggered rule, provide:
    - Complete token metadata
    - A clear description of the triggered rule
    - The relevant measured value
    - Supporting data that justifies the alert

    Please apply the rules as explicitly as possible and provide quantitative evidence where available.
    If you are planning to use another tool following your analysis, please ensure to format your analysis accordingly.

    ### Trading Strategy

    #### Price Changes
    I want to be alerted when any of these price changes are detected:
    - +/- 1.5% in 5 minute timeframe
    - +/- 3% in 1 hour timeframe
    - +/- 10% in 24 hour timeframe
    """

    # Optional step to provide a custom system prompt.
    # If no custom system prompt is provided, a default one will be used.
    with open(BASE_PATH / "lab/research_agent/research_agent_system_prompt.txt", "r") as f:
        system_prompt = f.read()

    system_prompt = system_prompt.replace("{{my_tokens}}", json.dumps(my_tokens))
    system_prompt = system_prompt.replace("{{specialization}}", specialization)

    agent = AlphaSwarmAgent(tools=tools, model_id="anthropic/claude-3-5-sonnet-20240620", system_prompt=system_prompt)

    terminal = TerminalClient("AlphaSwarm terminal", agent)
    await asyncio.gather(
        terminal.start(),
    )


if __name__ == "__main__":
    asyncio.run(main())
