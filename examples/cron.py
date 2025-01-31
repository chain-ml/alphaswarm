import asyncio
import logging
import random
from typing import List

import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.agent.clients import CronJobClient
from alphaswarm.config import Config
from alphaswarm.tools.alchemy import AlchemyPriceHistory
from alphaswarm.tools.exchanges import GetTokenPriceTool
from alphaswarm.tools.price_tool import PriceTool
from smolagents import Tool

logging.getLogger("smolagents").setLevel(logging.ERROR)


async def main():
    # Initialize the manager with your tools
    dotenv.load_dotenv()
    config = Config()

    tools: List[Tool] = [PriceTool(), GetTokenPriceTool(config), AlchemyPriceHistory()]  # Add you
    agent = AlphaSwarmAgent(tools=tools, model_id="gpt-4o")  # r tools here

    def generate_message_cron_job1() -> str:
        c = random.choice(["ETH", "BTC", "bitcoin", "weth", "quit"])
        return f"What's the value of {c}?" if c != "quit" else c

    def generate_message_cron_job2() -> str:
        c = random.choice(["What's the price history for ETH?", "What's the pair price of GIGA/SOL?", "quit"])
        return c

    def response_handler(prefix: str):
        def handler(response: str):
            print(f"\033[94m[{prefix}] Received response: {response}\033[0m")

        return handler

    # Create a cron job client that runs every 60 seconds
    cron_client_1 = CronJobClient(
        agent=agent,
        client_id="AlphaSwarm1",
        interval_seconds=60,
        message_generator=generate_message_cron_job1,
        response_handler=response_handler("AlphaSwarm1"),
    )

    cron_client_2 = CronJobClient(
        agent=agent,
        client_id="AlphaSwarm2",
        interval_seconds=15,
        message_generator=generate_message_cron_job2,
        response_handler=response_handler("AlphaSwarm2"),
    )

    await asyncio.gather(
        cron_client_1.start(),
        cron_client_2.start(),
    )


if __name__ == "__main__":
    asyncio.run(main())
