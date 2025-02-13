import asyncio
import datetime
import logging
from typing import List, Optional

import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.agent.clients import CronJobClient
from alphaswarm.services.alchemy import AlchemyClient
from alphaswarm.tools.alchemy import TokenPriceChangeCalculator


class PriceChangeObserver(AlphaSwarmAgent):
    def __init__(
        self,
        token_addresses: List[str],
        chain: str = "base-mainnet",
        price_change_interval: str = "1h",
        price_pct_chg_thresh: float = 2.0,
    ) -> None:
        """
        A basic agent that observes price changes for a set of token addresses.
        This agent does not use any LLM calls, instead it will just execute a sequence of tool calls.
        It can be adapted to use any LLM by adding logic to thea `process_message` method.

        Args:
            token_addresses: List of token addresses to observe
            chain: Chain to observe
            price_change_interval: Interval to observe
            price_pct_chg_thresh: Percentage change threshold to observe
        """

        self.alchemy_client = AlchemyClient.from_env()
        self.price_change_calculator = TokenPriceChangeCalculator(self.alchemy_client)
        self.token_addresses = token_addresses
        self.chain = chain
        self.price_change_interval = price_change_interval
        self.price_pct_chg_thresh = price_pct_chg_thresh

        hints = "Have any of the price changes increased or decreased (+/- 1%) since the last observation? Respond with either 'yes' or 'no'."

        super().__init__(model_id="gpt-4o-mini", tools=[], hints=hints)

    def get_price_alerts(self) -> str:
        """
        Get the price alerts for the token addresses.
        """
        price_alerts = []
        for address in self.token_addresses:
            price_history = self.price_change_calculator.forward(
                token_address=address,
                frequency=self.price_change_interval,
                n_samples=2,
                network=self.chain,
            )

            if abs(price_history.percent_change) >= self.price_pct_chg_thresh:
                price_alerts.append(
                    f"{address}: {price_history.percent_change}% change in the last {self.price_change_interval}."
                )

        logging.info(f"{len(price_alerts)} price alerts found.")
        if len(price_alerts) > 0:
            alert_message = f"Price changes have been observed for the following tokens as of {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: "
            alert_message += "\n" + "\n".join(price_alerts)
            return alert_message
        else:
            return ""

    # async def process_message(self, message: str) -> Optional[str]:
    #     """
    #     You can override the `process_message` method to specify how the agent will respond to the price alerts.
    #     When this method is not overridden, the default LLM-based agent configuration will be used to respond.
    #     """
    #     logging.info(f"Agent received alerts:\n{message}")
    #     pass


async def main() -> None:
    dotenv.load_dotenv()
    logging.basicConfig(level=logging.INFO)
    token_addresses = [
        "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825",  # AIXBT
        "0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b",  # VIRTUAL
        "0x731814e491571A2e9eE3c5b1F7f3b962eE8f4870",  # VADER
    ]

    agent = PriceChangeObserver(
        token_addresses=token_addresses,
        chain="base-mainnet",
        price_change_interval="5m",  # '5m', '1h', or '1d'
        price_pct_chg_thresh=0.02,
    )

    cron_client = CronJobClient(
        agent=agent,
        client_id="Price Change Observer",
        interval_seconds=5,
        response_handler=lambda _: None,
        message_generator=agent.get_price_alerts,
        should_process=lambda alerts: len(alerts) > 0,
        skip_message=lambda _: None,
        max_history=2,
    )
    await asyncio.gather(cron_client.start())


if __name__ == "__main__":
    asyncio.run(main())
