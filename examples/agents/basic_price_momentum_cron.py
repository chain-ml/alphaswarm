import asyncio
import datetime
import dotenv
import logging
from decimal import Decimal
from typing import List, Tuple

from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.agent.clients import CronJobClient
from alphaswarm.config import Config
from alphaswarm.services.alchemy import AlchemyClient
from alphaswarm.tools.get_token_address import GetTokenAddress
from alphaswarm.tools.alchemy import AlchemyPriceHistoryByAddress
from alphaswarm.tools.exchanges import ExecuteTokenSwapTool, GetTokenPriceTool


class PriceMomentumCronAgent(AlphaSwarmAgent):
    def __init__(
        self,
        token_addresses: List[str],
        chain: str = "base-mainnet",
        short_term_minutes: int = 5,
        short_term_threshold: float = 2.0,
        long_term_minutes: int = 60,
        long_term_threshold: float = 5.0,
    ) -> None:
        """  
        A price momentum agent that alerts on significant price movements.
        Price movements must exceed both thresholds and be in the same direction.

        Args:
            token_addresses: List of token addresses to observe
            chain: Chain to observe
            short_term_minutes: Number of minutes for short-term window (must be multiple of 5)
            short_term_threshold: Percentage threshold for short-term price change
            long_term_minutes: Number of minutes for long-term window (must be multiple of 5)
            long_term_threshold: Percentage threshold for long-term price change
        """
        if short_term_minutes % 5 != 0 or long_term_minutes % 5 != 0:
            raise ValueError("Time windows must be multiples of 5 minutes")
        if short_term_minutes >= long_term_minutes:
            raise ValueError("Long-term window must be larger than short-term window")

        self.alchemy_client = AlchemyClient.from_env()
        self.config = Config()
        self.price_history_tool = AlchemyPriceHistoryByAddress(self.alchemy_client)
        self.token_addresses = token_addresses
        self.chain = chain
        
        self.short_term_periods = short_term_minutes // 5
        self.long_term_periods = long_term_minutes // 5
        self.short_term_threshold = Decimal(str(short_term_threshold))
        self.long_term_threshold = Decimal(str(long_term_threshold))

        tools = [
            GetTokenAddress(config=self.config),
            GetTokenPriceTool(config=self.config),
            ExecuteTokenSwapTool(config=self.config)
        ]

        hints = "Please follow these task-specific instructions:"
        hints += "When you receive a positive price momentum alert, try to swap 0.0001 WETH for the token."
        hints += "When you receive a negative price momentum alert, do nothing, because you don't have access to your wallet balances."

        super().__init__(model_id="anthropic/claude-3-5-sonnet-20241022", tools=tools, hints=hints)

    def calculate_price_changes(self, prices: List[Decimal]) -> Tuple[Decimal, Decimal]:
        """Calculate short and long term price changes."""
        if len(prices) < self.long_term_periods:
            return Decimal('0'), Decimal('0')
            
        current_price = prices[-1]
        short_term_start = prices[-self.short_term_periods-1]
        long_term_start = prices[-self.long_term_periods-1]
        
        short_term_change = ((current_price - short_term_start) / short_term_start) * Decimal('100')
        long_term_change = ((current_price - long_term_start) / long_term_start) * Decimal('100')
        
        return short_term_change, long_term_change

    def get_price_alerts(self) -> str:
        """Get price alerts based on configured thresholds."""
        price_alerts = []
        for address in self.token_addresses:

            logging.info(f"Getting price history for {address}")
            price_history = self.price_history_tool.forward(
                address=address,
                network=self.chain,
                interval="5m",
                history=1  # 1 day of history
            )
            
            prices = [price.value for price in price_history.data]  # This is how to get the prices (Decimal type) out of the price history object
            short_term_change, long_term_change = self.calculate_price_changes(prices)
            
            # Check if changes meet thresholds and are in same direction
            short_term_signal = abs(short_term_change) >= self.short_term_threshold
            long_term_signal = abs(long_term_change) >= self.long_term_threshold
            same_direction = (short_term_change * long_term_change > Decimal('0'))
            
            # Alert only if both signals are present and in same direction
            if short_term_signal and long_term_signal and same_direction:
                direction = "Upward" if short_term_change > Decimal('0') else "Downward"
                price_alerts.append(
                    f"{address} --- {direction} momentum detected:\n"
                    f"  - {self.short_term_periods * 5}min change: {short_term_change:.2f}%\n"
                    f"  - {self.long_term_periods * 5}min change: {long_term_change:.2f}%"
                )

            logging.info(f"Short term change: {short_term_change:.2f}%")
            logging.info(f"Long term change: {long_term_change:.2f}%")

        logging.info(f"{len(price_alerts)} price alerts found.")
        if len(price_alerts) > 0:
            alert_message = f"Price changes have been observed for the following tokens as of {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: "
            alert_message += "\n" + "\n".join(price_alerts)
            return alert_message
        else:
            return ""


async def main() -> None:
    dotenv.load_dotenv()
    logging.basicConfig(level=logging.INFO)
    token_addresses = [
        "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825",  # AIXBT
        "0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b",  # VIRTUAL
        "0x731814e491571A2e9eE3c5b1F7f3b962eE8f4870",  # VADER
    ]

    agent = PriceMomentumCronAgent(
        token_addresses=token_addresses,
        chain="base-mainnet",
        short_term_minutes=5,
        short_term_threshold=0.2,
        long_term_minutes=60,
        long_term_threshold=2.0,
    )

    cron_client = CronJobClient(
        agent=agent,
        client_id="Price Momentum Cron Agent",
        interval_seconds=300,  # 5 minutes
        response_handler=lambda _: None,
        message_generator=agent.get_price_alerts,
        should_process=lambda alerts: len(alerts) > 0,
        skip_message=lambda _: None,
        max_history=0,
    )
    await asyncio.gather(cron_client.start())


if __name__ == "__main__":
    asyncio.run(main())
