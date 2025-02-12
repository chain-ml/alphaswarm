import asyncio
import logging
from typing import Callable, List

import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.agent.clients import CronJobClient
from alphaswarm.config import Config
from alphaswarm.tools.alchemy import AlchemyPriceHistoryBySymbol
from alphaswarm.tools.exchanges import GetTokenPriceTool
from alphaswarm.tools.price_tool import PriceTool
from smolagents import Tool

logging.getLogger("smolagents").setLevel(logging.ERROR)


async def main() -> None:
    dotenv.load_dotenv()
    config = Config()

    # Initialize tools for price-related operations
    # GetTokenPriceTool: Real-time token prices
    # AlchemyPriceHistoryBySymbol: Historical price data from Alchemy
    tools: List[Tool] = [GetTokenPriceTool(config), AlchemyPriceHistoryBySymbol()]  # TODO: what tools to use

    # Initialize the AlphaSwarm agent with the price tools
    agent = AlphaSwarmAgent(tools=tools, model_id="anthropic/claude-3-5-sonnet-20241022")

    price_tool = PriceTool()

    def generate_message() -> str:
        # Call price tool and see if there's a 24h price change more than `threshold`%

        address = "0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b".lower()  # VIRTUAL
        chain = "base"
        threshold = 10  # in percentages

        data = price_tool.fetch_price(address=address, chain=chain).json()
        change_24h = data[address]["usd_24h_change"]
        if abs(change_24h) >= threshold:
            return f"Alert! {address} change on {chain} is {change_24h:+.2f}%"

        return (
            f"No alerts, {address} change on {chain} is {change_24h:+.2f}%, "
            f"monitoring for at least {threshold:.2f}% change..."
        )

    def should_process_message(message: str) -> bool:
        return message.startswith("Alert!")

    def handle_skipped(message: str) -> None:
        print(f"Skipped processing message: {message}")

    def response_handler(prefix: str) -> Callable[[str], None]:
        # Creates a closure that prints responses with color formatting
        def handler(response: str) -> None:
            print(f"\033[94m[{prefix}] Received response: {response}\033[0m")

        return handler

    cron_client = CronJobClient(
        agent=agent,
        client_id="AlphaSwarm Observer Example",
        interval_seconds=5,
        message_generator=generate_message,
        response_handler=response_handler("AlphaSwarm Observer Example"),
        should_process=should_process_message,
        skip_message=handle_skipped,
    )
    await asyncio.gather(cron_client.start())


if __name__ == "__main__":
    asyncio.run(main())
