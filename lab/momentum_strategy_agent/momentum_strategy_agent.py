import asyncio
import json
from typing import List

import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.agent.clients import TerminalClient
from alphaswarm.config import CONFIG_PATH, Config
from alphaswarm.tools.cookie.cookie_metrics import CookieMetricsByContract
from alphaswarm.tools.exchanges.execute_token_swap_tool import ExecuteTokenSwapTool
from alphaswarm.tools.exchanges.get_token_price_tool import GetTokenPriceTool
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
            GetTokenPriceTool(config=config),
            CookieMetricsByContract(),
            ExecuteTokenSwapTool(config=config),
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
        Send an alert (possibly with a trade proposal) when any of the following triggers are met:

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
        - Triggered Rules (Current Value And Rule Thresholds )
        - Current Key Values
        - Link to tweets that could explain why the rule(s) triggered
        - Any other correlated signals
        - Concrete trade proposal (if applicable, see below)
        """

        trading_venues = config.get_trading_venues()

        hints = f"""## Confirming Trade Proposals
        You have the ability to assist the user with making trades via the `execute_token_swap` tool.
        Critically, you must ALWAYS ask for confirmation of inputs before invoking the `execute_token_swap` tool.
        Since you do not have access to the user's wallet balances, you must propose everything for the user except for the amount of quote token to swap.
        Let the user tell you how much of the quote token (the token being sold) they want to swap for the base token (the token being bought).
        
        ## Trading Venues
        The available trading venues are:
        {trading_venues}
        """

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
