import asyncio
import json
from typing import List

import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.agent.clients import TerminalClient
from alphaswarm.config import BASE_PATH, Config
from alphaswarm.tools.exchanges.execute_token_swap_tool import ExecuteTokenSwapTool
from alphaswarm.tools.exchanges.get_token_price_tool import GetTokenPriceTool
from alphaswarm.tools.telegram import SendTelegramNotificationTool
from lab.trade_advisor_agent.tools.call_forecasting_agent_tool import CallForecastingAgentTool
from smolagents import Tool


class TradeAdvisorAgent(AlphaSwarmAgent):
    def __init__(self) -> None:
        config = Config()
        telegram_config = config.get("telegram", {})
        telegram_bot_token = telegram_config.get("bot_token")
        chat_id = int(telegram_config.get("chat_id"))

        tools: List[Tool] = [
            CallForecastingAgentTool(),
            GetTokenPriceTool(config=config),
            ExecuteTokenSwapTool(config=config),
            SendTelegramNotificationTool(telegram_bot_token=telegram_bot_token, chat_id=chat_id),
        ]

        my_tokens = {
            "AIXBT (base)": "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825",
            "VIRTUAL (base)": "0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b",
            "VADER (base)": "0x731814e491571A2e9eE3c5b1F7f3b962eE8f4870",
            "COOKIE (base)": "0xc0041ef357b183448b235a8ea73ce4e4ec8c265f",
        }

        trading_venues = config.get_trading_venues()

        specialization = f"""
        # Trade Proposal Generator

        Generate high-conviction trade proposals based on forecasts.
        Use forecasting agent for predictions and validate thoroughly.

        ## High Conviction Trade Rules (>=70% confidence)
        - 5min: >1% predicted move
        - 1hr: >2% predicted move
        - 6hr: >3% predicted move
        Requirements:
        - Full agreement with forecast reasoning
        - Normal volatility verified

        Do not propose trades if:
        - Confidence < 70%
        - Flawed reasoning found
        - Extreme volatility detected

        ## Making and Confirming Trade Proposals
        You have the ability to assist the user with making trades via the `execute_token_swap` tool.
        Critically, you must ALWAYS ask for confirmation of inputs before invoking the `execute_token_swap` tool.
        Since you do not have access to the user's wallet balances, you must propose everything for the user except for the amount of quote token to swap.
        Let the user tell you how much of the quote token (the token being sold) they want to swap for the base token (the token being bought).

        # Trading Venues
        You can only trade on the following venues:
        {trading_venues}
        """

        workflows = "You must always propose trades before executing them."

        hints = "When requesting a forecast over a horizon `h`, request to use `10*h` units of historical data."
        hints += "When introducing yourself, describe yourself as a 'trading advisor' and mention that a 'forecasting expert' is part of your swarm."
        hints += "If you have executed a trade successfully, be sure to set confidence to 100% when sending a telegram notification."
        hints += "Prioritize Uniswap V3 for trading."
        hints += "Make sure you observe the outcome of a trade before generating any result messages."
        hints += "When a trade is unsuccessful, do not adjust any inputs, instead ask the user for confirmation to try again."

        try:
            system_prompt = open(BASE_PATH / "lab/research_agent_system_prompt.txt", "r").read()
        except FileNotFoundError:
            system_prompt = ""

        system_prompt = system_prompt.replace("{{my_tokens}}", json.dumps(my_tokens))
        system_prompt = system_prompt.replace("{{specialization}}", specialization)
        system_prompt = system_prompt.replace("{{workflows}}", workflows)
        super().__init__(
            tools=tools,
            model_id="anthropic/claude-3-5-sonnet-20241022",
            system_prompt=system_prompt,
            hints=hints,
        )


async def main() -> None:
    dotenv.load_dotenv()

    agent = TradeAdvisorAgent()
    terminal = TerminalClient("AlphaSwarm terminal", agent)
    await asyncio.gather(
        terminal.start(),
    )


if __name__ == "__main__":
    asyncio.run(main())
