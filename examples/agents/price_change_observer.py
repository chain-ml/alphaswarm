import asyncio
import dotenv
from enum import Enum
import logging
from typing import List, Optional

from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.agent.clients import TerminalClient, CronJobClient
from alphaswarm.config import BASE_PATH, Config
from alphaswarm.tools.alchemy import TokenPriceChangeCalculator
from alphaswarm.services.alchemy import AlchemyClient

class PriceChangeInterval(Enum):
    FIVE_MINUTES: str = "5m"
    ONE_HOUR: str = "1h"
    ONE_DAY: str = "1d"


"""
TODO: Finish this in the morning -- we just want the agent to execute a sequence of tool calls,
with some logic to apply thresholds or whatever.

The point is not that this is needed for this example, but rather that the pattern still works.

In another example, we'll have an agent that is generating forecasts, which could absoultely use the 'agentic' pattern. 
"""

class PriceChangeObserver(AlphaSwarmAgent):
    def __init__(
        self,
        token_addresses: List[str],
        chain: str = "base-mainnet",
        price_change_interval: str = PriceChangeInterval.ONE_HOUR,
        price_change_percentage: float = 2.0,
    ) -> None:
        """
        Initialize the PriceChangeObserver with some `configurable` parameters.
        This `agent` won't use any LLM calls, rather it will just execute a sequence of tool calls.
        It may imply that we want to generalize AlphSwarmAgent so that it doesn't necessarily need a LLM or smolagents.

        Args:
            token_addresses: List of token addresses to observe
            chain: Chain to observe
            price_change_interval: Interval to observe
            price_change_percentage: Percentage to observe
        """

        self.alchemy_client = AlchemyClient.from_env()
        self.price_change_calculator = TokenPriceChangeCalculator(self.alchemy_client)
        self.token_addresses = token_addresses
        self.chain = chain
        self.price_change_interval = price_change_interval
        self.price_change_percentage = price_change_percentage

        super().__init__(tools=[self.price_change_calculator])

    async def process_message(self, current_message: str) -> Optional[str]:
        # It doesn't matter what the message is, we just want to 'execute' a sequence of tool calls
        logging.info(f"Processing message: {current_message}")

        # Get the price history
        price_alerts = []
        for address in self.token_addresses:
            logging.info(f"Processing token address: {address}")
            price_history = self.price_change_calculator.forward(
                token_address=address,
                frequency=self.price_change_interval,
                n_samples=2,
                network=self.chain,
            )
            logging.info(f"Price history: {price_history}")
            if price_history.percent_change >= self.price_change_percentage:
                price_alerts.append(f"Price alert for {address}: {price_history.percent_change}% change in the last {self.price_change_interval}.")
        
        if len(price_alerts) > 0:
            return "\n".join(price_alerts)
        else:
            return "No price alerts found."


async def main() -> None:
    dotenv.load_dotenv()
    logging.basicConfig(level=logging.INFO)
    token_addresses = [
        "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825",
        "0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b",
        "0x731814e491571A2e9eE3c5b1F7f3b962eE8f4870",
    ]

    agent = PriceChangeObserver(
        token_addresses=token_addresses,
        chain="base-mainnet",
        price_change_interval="1h",
        price_change_percentage=2.0,
    )

    cron_client = CronJobClient(
        agent=agent,
        client_id="AlphaSwarm Observer Example",
        interval_seconds=5,
        message_generator=lambda: "Check the price history for any alerts.",
        should_process=lambda _: True,
        skip_message=lambda _: None,
    )
    await asyncio.gather(cron_client.start())


if __name__ == "__main__":
    asyncio.run(main())
