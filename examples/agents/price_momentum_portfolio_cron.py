import asyncio
import datetime
import logging
from decimal import Decimal
from typing import List, Tuple

import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.agent.clients import CronJobClient
from alphaswarm.config import Config
from alphaswarm.services.alchemy import AlchemyClient
from alphaswarm.tools.alchemy import GetAlchemyPriceHistoryByAddress
from alphaswarm.tools.exchanges import ExecuteTokenSwap, GetTokenPrice
from alphaswarm.tools.core import GetTokenAddress
from alphaswarm.tools.portfolio import GetPortfolioBalance


class PriceMomentumCronAgent(AlphaSwarmAgent):
    def __init__(
        self,
        token_addresses: List[str],
        chain: str = "base-mainnet",
        short_term_minutes: int = 5,
        short_term_threshold: float = 2.0,
        long_term_minutes: int = 60,
        long_term_threshold: float = 5.0,
        max_possible_percentage: Decimal = Decimal("5"),  # Max 5% per trade
        absolute_min_amount: Decimal = Decimal("0.0001"),  # 0.0001 WETH minimum
        base_token: str = "WETH",
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
            max_possible_percentage: Maximum percentage of portfolio to allocate to any single trade
            absolute_min_amount: Minimum amount of portfolio to maintain in base_token
            base_token: Base token to maintain in portfolio
        """
        if short_term_minutes % 5 != 0 or long_term_minutes % 5 != 0:
            raise ValueError("Time windows must be multiples of 5 minutes")
        if short_term_minutes >= long_term_minutes:
            raise ValueError("Long-term window must be larger than short-term window")

        self.alchemy_client = AlchemyClient.from_env()
        self.config = Config()
        self.price_history_tool = GetAlchemyPriceHistoryByAddress(self.alchemy_client)
        self.portfolio_tool = GetPortfolioBalance(config=self.config)
        self.token_addresses = token_addresses
        self.chain = chain

        self.short_term_periods = short_term_minutes // 5
        self.long_term_periods = long_term_minutes // 5
        self.short_term_threshold = Decimal(str(short_term_threshold))
        self.long_term_threshold = Decimal(str(long_term_threshold))
        
        self.max_possible_percentage = max_possible_percentage
        self.absolute_min_amount = absolute_min_amount
        self.base_token = base_token

        tools = [
            GetTokenAddress(config=self.config),
            GetTokenPrice(config=self.config),
            ExecuteTokenSwap(config=self.config),
        ]

        hints = "Please try to perform the requested swaps."

        super().__init__(model_id="anthropic/claude-3-5-sonnet-20241022", tools=tools, hints=hints)

    def calculate_price_changes(self, prices: List[Decimal]) -> Tuple[Decimal, Decimal]:
        """Calculate short and long term price changes."""
        if len(prices) < self.long_term_periods:
            return Decimal("0"), Decimal("0")

        current_price = prices[-1]
        short_term_start = prices[-self.short_term_periods - 1]
        long_term_start = prices[-self.long_term_periods - 1]

        short_term_change = ((current_price - short_term_start) / short_term_start) * Decimal("100")
        long_term_change = ((current_price - long_term_start) / long_term_start) * Decimal("100")

        return short_term_change, long_term_change

    def get_portfolio_balance_info(self) -> str:
        """Generate formatted portfolio balance information."""
        tokens = self.portfolio_tool.forward(chain=self.chain)
        balance_info = ["```csv", "address,amount"]
        for token in tokens:
            balance_info.append(f"{token.token_info.address},{token.value}")
        balance_info.append("```")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logging.info("Portfolio Balance retrieved")
        return f"=== Portfolio Balance Summary at {timestamp} ===\n{'\n'.join(balance_info)}"    


    def get_price_history_info(self) -> str:
        """Generate price history information for tokens."""
        signals = []
        for address in self.token_addresses:
            logging.info(f"Getting price history for {address}")
            
            price_history = self.price_history_tool.forward(
                address=address, 
                # TODO: this is a hack to get the correct network from chain, probably should 
                # modify get_historical_prices_by_address to take in chain as a parameter instead of network
                network=self.price_history_tool.client.chain_to_network(self.chain),
                interval="5m",
                history=1  # 1 day of history
            )
            
            prices = [
                price.value for price in price_history.data
            ]
            short_term_change, long_term_change = self.calculate_price_changes(prices)

            # Check if changes meet thresholds and are in same direction
            short_term_signal = abs(short_term_change) >= self.short_term_threshold
            long_term_signal = abs(long_term_change) >= self.long_term_threshold
            same_direction = short_term_change * long_term_change > Decimal("0")

            # Log all signals for monitoring
            logging.info(f"{self.short_term_periods * 5} minute change: {short_term_change:.2f}%")
            logging.info(f"{self.long_term_periods * 5} minute change: {long_term_change:.2f}%")

            # Only generate trade instructions for positive momentum
            if short_term_signal and long_term_signal and same_direction:
                # buy signal
                if short_term_change > 0:
                    momentum_str = f"Strong upward momentum detected for {address}:\n"
                    logging.info(momentum_str)
                # sell signal
                elif short_term_change < 0:
                    momentum_str = f"Strong downward momentum detected for {address}:\n"
                    logging.info(momentum_str)
                signals.append(momentum_str +
                               f"  - {self.short_term_periods * 5}min change: +{short_term_change:.2f}%\n"
                               f"  - {self.long_term_periods * 5}min change: +{long_term_change:.2f}%")
        if not signals:
            return ""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"=== Momentum Trade Signal Found at {timestamp} ===\n{'\n'.join(signals)}"
    

    def get_trade_alerts(self) -> str:
        """Get trade instructions with portfolio-aware sizing."""
        # Get momentum signals
        momentum_signals = self.get_price_history_info()
        if not momentum_signals:
            return ""
        
        # Get portfolio balance
        portfolio_info = self.get_portfolio_balance_info()

        # Construct AI prompt with context
        response = (
            f"{portfolio_info}\n\n"
            f"{momentum_signals}\n\n"
            "=== Trading Strategy Requirements (must be followed) ===\n"
            # TODO: how would the agent know this percentage of portfolio if things are not being translated to USD?
            f"1. Allocate maximum {self.max_possible_percentage}% of portfolio to any single trade\n"
            f"2. Prefer tokens with strongest combined momentum\n"
            f"3. Maintain minimum {self.absolute_min_amount} portfolio in {self.base_token}\n"
            "4. Consider price impact and liquidity\n"
            "Please decide if you want to trade based on the above information and requirements and how much you want to trade for which token.\n"
            "Provide your reasonings before making the final decision."
        )

        return response


async def main() -> None:
    dotenv.load_dotenv()

    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )

    token_addresses = [
        "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825",  # AIXBT
        "0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b",  # VIRTUAL
        "0x731814e491571A2e9eE3c5b1F7f3b962eE8f4870",  # VADER
    ]

    agent = PriceMomentumCronAgent(
        token_addresses=token_addresses,
        chain="base",
        short_term_minutes=5,
        short_term_threshold=0.1,
        long_term_minutes=60,
        long_term_threshold=0.5,
    )

    cron_client = CronJobClient(
        agent=agent,
        client_id="Price Momentum Cron Agent With Portfolio Balance",
        interval_seconds=300,  # 5 minutes
        response_handler=lambda _: None,
        message_generator=agent.get_trade_alerts,
        should_process=lambda alerts: len(alerts) > 0,
        skip_message=lambda _: None,
        max_history=2,  # Last message pair only
    )
    await asyncio.gather(cron_client.start())


if __name__ == "__main__":
    asyncio.run(main())
