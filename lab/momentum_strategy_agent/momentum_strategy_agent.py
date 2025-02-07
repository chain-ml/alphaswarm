import asyncio
import json
from typing import List

import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.agent.clients import TerminalClient
from alphaswarm.config import CONFIG_PATH, Config
from alphaswarm.tools.cookie.cookie_metrics import CookieMetricsByContract
from alphaswarm.tools.telegram import SendTelegramNotificationTool
from lab.momentum_strategy_agent.tools.price_change_tool import TokenPriceChangeCalculator
from smolagents import Tool


class MomentumStrategyAgent(AlphaSwarmAgent):
    def __init__(self) -> None:
        config = Config()
        telegram_config = config.get("telegram", {})
        telegram_bot_token = telegram_config.get("bot_token")
        chat_id = int(telegram_config.get("chat_id"))

        tools: List[Tool] = [
            TokenPriceChangeCalculator(),
            CookieMetricsByContract(),
            SendTelegramNotificationTool(telegram_bot_token=telegram_bot_token, chat_id=chat_id),
        ]

        my_tokens = {
            "AIXBT (base)": "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825",
            "VIRTUAL (base)": "0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b",
            "VADER (base)": "0x731814e491571A2e9eE3c5b1F7f3b962eE8f4870",
            "COOKIE (base)": "0xc0041ef357b183448b235a8ea73ce4e4ec8c265f",
        }

        trading_strategy = """
        # Social + Market Momentum Strategy

        Monitor tokens for significant changes in both price action and social metrics.
        Use price data from TokenPriceChangeCalculator and social metrics from cookie.fun.
        Send an alert when any of the following triggers are met:

        ## Triggers

        Price Changes:
        - ±1.5% / 5min
        - ±3% / 1hr
        - ±10% / 24hr

        Cookie.fun Metrics (3-day changes):
        - Volume: ±30%
        - Market Cap: ±10%
        - Mindshare: ±50%
        - Followers: ±10%

        # Alert Contents
        - Token + Token Address + Direction
        - Triggered Rules (Current Value And Rule Thresholds)
        - Current Key Values
        - Link to tweets that could explain why the rule(s) triggered
        - Any other correlated signals
        """

        hints = """Quantize decimal values when presenting them to the user for readability. Use following code:
        `formatted_value = decimal_value.quantize(Decimal("0.0001"))`  # from decimal import Decimal"""

        try:
            system_prompt = open(CONFIG_PATH / "trading_strategy_agent_system_prompt.txt", "r").read()
        except FileNotFoundError:
            system_prompt = ""

        system_prompt = system_prompt.replace("{{token_name_to_address}}", json.dumps(my_tokens))
        system_prompt = system_prompt.replace("{{trading_strategy}}", trading_strategy)

        super().__init__(
            tools=tools,
            model_id="anthropic/claude-3-5-sonnet-20241022",
            system_prompt=system_prompt,
            hints=hints,
        )


async def main() -> None:
    dotenv.load_dotenv()

    agent = MomentumStrategyAgent()
    terminal = TerminalClient("AlphaSwarm terminal", agent)
    await asyncio.gather(
        terminal.start(),
    )


if __name__ == "__main__":
    asyncio.run(main())
