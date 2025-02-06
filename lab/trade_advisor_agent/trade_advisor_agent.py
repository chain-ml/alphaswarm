import asyncio
import json
from typing import List

import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.agent.clients import TerminalClient
from alphaswarm.config import BASE_PATH, Config
from alphaswarm.tools.telegram import SendTelegramNotificationTool
from lab.trade_advisor_agent.tools.call_forecasting_agent_tool import CallForecastingAgentTool
from smolagents import Tool


class TradeAdvisorAgent(AlphaSwarmAgent):
    def __init__(self):
        config = Config()
        telegram_config = config.get("telegram", {})
        telegram_bot_token = telegram_config.get("bot_token")
        chat_id = int(telegram_config.get("chat_id"))

        tools: List[Tool] = [
            SendTelegramNotificationTool(telegram_bot_token=telegram_bot_token, chat_id=chat_id),
            CallForecastingAgentTool(),
        ]

        my_tokens = {
            "AIXBT (base)": "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825",
            "VIRTUAL (base)": "0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b",
            "VADER (base)": "0x731814e491571A2e9eE3c5b1F7f3b962eE8f4870",
            # "AI16Z": "HeLp6NuQkmYB4pYWo2zYs22mESHXPQYzXbB8n4V98jwC",
            # "GRIFFAIN": "8x5VqbHA8D7NkD52uNuS5nnt3PwA8pLD34ymskeSo2Wn",
        }

        specialization = """
        # Trading Signal Generator

        Evaluate price forecasts and generate high-conviction trading signals.
        Use forecasting agent for predictions and independently validate signals.

        ## Signal Generation Rules

        High Conviction (>80% confidence):
        - 5min: >2% predicted move
        - 1hr: >4% predicted move
        - 6hr: >7% predicted move
        Requirements:
        - Full agreement with forecast reasoning
        - Normal volatility verified

        Moderate Conviction (60-80% confidence):
        - 5min: >3% predicted move
        - 1hr: >6% predicted move
        - 6hr: >10% predicted move
        Requirements:
        - Mostly agree with analysis
        - At least one verified catalyst

        ## Signal Format
        - Token Name + Direction (e.g. "AIXBT ⬆️ Buy Signal")
        - Timeframe + Expected Move
        - Confidence Level
        - Key Supporting Points
        - Risk Factors

        Do not signal if:
        - Confidence < 60%
        - Flawed reasoning found
        - Extreme volatility detected
        """

        try:
            system_prompt = open(BASE_PATH / "lab/research_agent_system_prompt.txt", "r").read()
        except FileNotFoundError:
            system_prompt = ""

        system_prompt = system_prompt.replace("{{my_tokens}}", json.dumps(my_tokens))
        system_prompt = system_prompt.replace("{{specialization}}", specialization)

        super().__init__(tools=tools, model_id="anthropic/claude-3-5-sonnet-20241022", system_prompt=system_prompt)


async def main() -> None:
    dotenv.load_dotenv()

    agent = TradeAdvisorAgent()
    terminal = TerminalClient("AlphaSwarm terminal", agent)
    await asyncio.gather(
        terminal.start(),
    )


if __name__ == "__main__":
    asyncio.run(main())
