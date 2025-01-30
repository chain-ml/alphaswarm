import asyncio
import logging
import random
from typing import List

import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent, AlphaSwarmAgentManager
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
    manager = AlphaSwarmAgentManager(agent)

    def generate_message() -> str:
        return "What's the value of BTC?"

    def generate_message_2() -> str:
        b = random.choice([1, 2])
        return "What's the price history for ETH?" if b == 1 else "What's the pair price of GIGA/SOL?"

    def response_handler(prefix: str):
        def handler(response: str):
            print(f"\033[94m[{prefix}] Received response: {response}\033[0m")

        return handler

    # Create a cron job client that runs every 60 seconds
    cron_client_1 = CronJobClient(
        manager=manager,
        client_id="cron1",
        interval_seconds=60,
        message_generator=generate_message,
        response_handler=response_handler("CronJob1"),
    )

    cron_client_2 = CronJobClient(
        manager=manager,
        client_id="cron2",
        interval_seconds=45,
        message_generator=generate_message_2,
        response_handler=response_handler("CronJob2"),
    )

    await asyncio.gather(
        cron_client_1.start(),
        cron_client_2.start(),
    )


if __name__ == "__main__":
    asyncio.run(main())
