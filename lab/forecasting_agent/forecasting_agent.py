import asyncio
import os
from typing import List

import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.agent.clients import TerminalClient
from alphaswarm.config import BASE_PATH
from alphaswarm.tools.alchemy import AlchemyPriceHistoryBySymbol
from alphaswarm.tools.cookie.cookie_metrics import CookieMetricsPaged
from alphaswarm.tools.telegram import SendTelegramNotificationTool
from alphaswarm.utils.file_utils import read_text_file_to_string
from lab.forecasting_agent.price_forecasting_tool import PriceForecastingTool
from smolagents import Tool


class ForecastingAgent(AlphaSwarmAgent):
    def __init__(self) -> None:
        tools: List[Tool] = [
            # AlchemyContextTool(),
            AlchemyPriceHistoryBySymbol(),
            # CookieMetricsBySymbol(),
            CookieMetricsPaged(),
            PriceForecastingTool(),
            # DuckDuckGoSearchTool(),
            SendTelegramNotificationTool(
                telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"), chat_id=int(os.getenv("TELEGRAM_CHAT_ID"))
            ),
        ]

        system_prompt = read_text_file_to_string(
            BASE_PATH / "lab/research_agent_system_prompt.txt"
        )

        specialization = """
        ## Specialization
        You are specialized in making price forecasts for crypto assets.

        When doing this:
        1. Get the historical price data for the token
        2. Use additional tools to get market context that is relevant to predicting the price of a token
        3. Use may use more than one tool to get additional market context if needed and if available
        4. Use the forecasting tool to generate a price forecast
        5. Your final response must include the reasoning behind the forecast
        6. Use web search to gather any information that could be relevant for the context, 
        but be mindful about information relevance and recency.
        """

        system_prompt = system_prompt.replace("{{my_tokens}}", "")
        system_prompt = system_prompt.replace("{{specialization}}", specialization)

        super().__init__(tools=tools, model_id="anthropic/claude-3-5-sonnet-20241022", system_prompt=system_prompt)


async def main() -> None:
    dotenv.load_dotenv()

    agent = ForecastingAgent()

    terminal = TerminalClient("AlphaSwarm terminal", agent)
    await asyncio.gather(
        terminal.start(),
    )


if __name__ == "__main__":
    asyncio.run(main())
