import asyncio
import json
from typing import List

import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.agent.clients import TerminalClient
from alphaswarm.config import CONFIG_PATH, Config
from alphaswarm.tools.alchemy import AlchemyPriceHistoryByAddress, AlchemyPriceHistoryBySymbol
from alphaswarm.tools.exchanges import GetTokenPriceTool
from alphaswarm.tools.price_tool import PriceTool
from alphaswarm.tools.strategy_analysis.generic import GenericStrategyAnalysisTool
from alphaswarm.tools.strategy_analysis.strategy import Strategy
from alphaswarm.tools.telegram import SendTelegramNotificationTool
from alphaswarm.utils import read_text_file_to_string
from smolagents import Tool


async def main() -> None:
    dotenv.load_dotenv()
    config = Config()

    telegram_config = config.get("telegram", {})
    telegram_bot_token = telegram_config.get("bot_token")
    chat_id = int(telegram_config.get("chat_id"))

    strategy = Strategy.from_file(CONFIG_PATH / "momentum_strategy_config.md")

    tools: List[Tool] = [
        PriceTool(),
        GetTokenPriceTool(config),
        AlchemyPriceHistoryByAddress(),
        AlchemyPriceHistoryBySymbol(),
        GenericStrategyAnalysisTool(strategy=strategy),
        SendTelegramNotificationTool(telegram_bot_token=telegram_bot_token, chat_id=chat_id),
    ]  # Add your tools here

    # Optional step to provide a custom system prompt.
    # If no custom system prompt is provided, a default one will be used.
    system_prompt = read_text_file_to_string(CONFIG_PATH / "trading_strategy_agent_system_prompt.txt")

    token_set = {
        "AIXBT (base)": "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825",
        "VIRTUAL (base)": "0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b",
        "VADER (base)": "0x731814e491571A2e9eE3c5b1F7f3b962eE8f4870",
    }

    system_prompt = system_prompt.replace("{{trading_strategy}}", strategy.rules)
    system_prompt = system_prompt.replace("{{token_set}}", json.dumps(token_set))

    hints = """You must only use real data obtained through the available tools - never make up, synthesize, or assume any market data.
    If you don't have access to certain data through the tools, acknowledge the limitation rather than making assumptions.
    """

    agent = AlphaSwarmAgent(
        model_id="anthropic/claude-3-5-sonnet-20240620", tools=tools, system_prompt=system_prompt, hints=hints
    )

    terminal = TerminalClient("AlphaSwarm terminal", agent)
    await asyncio.gather(
        terminal.start(),
    )


if __name__ == "__main__":
    asyncio.run(main())
