import asyncio
from typing import List

import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.agent.clients import TerminalClient
from alphaswarm.config import BASE_PATH, Config
from alphaswarm.tools.alchemy import AlchemyPriceHistoryBySymbol
from alphaswarm.tools.cookie.cookie_metrics import CookieMetricsBySymbol, CookieMetricsPaged
from alphaswarm.tools.telegram import SendTelegramNotificationTool
from alphaswarm.utils.file_utils import read_text_file_to_string
from lab.forecasting_agent.tools.duck_duck_go_search_tool import DuckDuckGoSearchTool
from lab.forecasting_agent.tools.price_forecasting_tool import PriceForecastingTool

# from lab.forecasting_agent.alchemy_context_tool import AlchemyContextTool
from smolagents import Tool


class ForecastingAgent(AlphaSwarmAgent):
    def __init__(self) -> None:
        config = Config()
        telegram_config = config.get("telegram", {})
        telegram_bot_token = telegram_config.get("bot_token")
        chat_id = int(telegram_config.get("chat_id"))
        tools: List[Tool] = [
            # AlchemyContextTool(),
            AlchemyPriceHistoryBySymbol(),
            CookieMetricsBySymbol(),
            CookieMetricsPaged(),
            PriceForecastingTool(),
            DuckDuckGoSearchTool(),
            SendTelegramNotificationTool(
                telegram_bot_token=telegram_bot_token,
                chat_id=chat_id,
            ),
        ]

        system_prompt = read_text_file_to_string(BASE_PATH / "lab/research_agent_system_prompt.txt")

        specialization = """
        ## Specialization
        You are specialized in making price forecasts for crypto assets.
        You are an expert at doing research to establish the context for your forecasts.

        Your workflow:
        - Get the historical price data for the token
        - Conduct research using your available tools
        -- Use `CookieMetricsBySymbol` to get metrics about the subject token
        -- Use `CookieMetricsPaged` to get a broader market overview of related AI agent tokens
        - Conduct additional research using the same or other tools as needed
        - Use the forecasting tool to generate a price forecast
        - Present a final response that includes a justification for your forecast
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
