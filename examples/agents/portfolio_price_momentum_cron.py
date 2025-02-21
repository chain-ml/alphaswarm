import asyncio
import datetime
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Sequence

import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.agent.clients import CronJobClient
from alphaswarm.config import Config
from alphaswarm.services.alchemy import AlchemyClient
from alphaswarm.services.portfolio import Portfolio
from alphaswarm.tools.alchemy import GetAlchemyPriceHistoryByAddress
from alphaswarm.tools.core import GetTokenAddress
from alphaswarm.tools.exchanges import ExecuteTokenSwap, GetTokenPrice


@dataclass
class PriceChanges:
    short_term: Decimal
    long_term: Decimal

    @classmethod
    def null(cls) -> "PriceChanges":
        return cls(Decimal("0"), Decimal("0"))

    def is_above_threshold(self, short: Decimal, long: Decimal) -> bool:
        return (
            abs(self.short_term) >= short
            and abs(self.long_term) >= long
            and self.short_term * self.long_term > Decimal("0")
        )

    @classmethod
    def from_prices(cls, prices: Sequence[Decimal], *, short_period: int, long_period: int) -> "PriceChanges":
        if len(prices) < long_period:
            return cls.null()

        current_price = prices[-1]
        short_term_start = prices[-short_period - 1]
        long_term_start = prices[-long_period - 1]

        short_term = ((current_price - short_term_start) / short_term_start) * Decimal("100")
        long_term = ((current_price - long_term_start) / long_term_start) * Decimal("100")

        return cls(short_term, long_term)


class PriceMomentumCronAgent(AlphaSwarmAgent):
    """
    A portfolio-aware momentum trading agent that combines deterministic analysis
    with AlphaSwarm reasoning and tools for position sizing and trade execution.
    A `cron` task will continually monitor price changes and determine whether momentum criteria are met.
    If momentum criteria are met, a trading task will be generated for the agent to execute.
    """

    def __init__(
        self,
        token_addresses: List[str],
        chain: str = "base",
        short_term_minutes: int = 5,
        short_term_threshold: float = 2.0,
        long_term_minutes: int = 60,
        long_term_threshold: float = 5.0,
        max_possible_percentage: Decimal = Decimal("50"),
        absolute_min_amount: Decimal = Decimal("0.0001"),
        base_token: str = "WETH",
    ) -> None:
        """
        Initialize the PriceMomentumCronAgent.
        Args:
            token_addresses: List of token addresses to observe
            chain: Chain to observe
            short_term_minutes: Number of minutes for short-term window (must be multiple of 5)
            short_term_threshold: Percentage threshold for short-term price change
            long_term_minutes: Number of minutes for long-term window (must be multiple of 5)
            long_term_threshold: Percentage threshold for long-term price change
            max_possible_percentage: Maximum percentage of base_token to allocate to any single trade
            absolute_min_amount: Minimum amount of portfolio to maintain in base_token
            base_token: Base token to maintain in portfolio
        """
        if short_term_minutes % 5 != 0 or long_term_minutes % 5 != 0:
            raise ValueError(
                "Time windows must be multiples of 5 minutes, "
                f"got short_term_minutes {short_term_minutes} and long_term_minutes {long_term_minutes}"
            )
        if short_term_minutes >= long_term_minutes:
            raise ValueError(
                f"Long-term window {long_term_minutes} minutes must be larger than short-term window {short_term_minutes} minutes"
            )
        if max_possible_percentage <= 0 or max_possible_percentage > 100:
            raise ValueError(f"max_possible_percentage must be between 0 and 100, got {max_possible_percentage}")
        if absolute_min_amount <= 0:
            raise ValueError(f"absolute_min_amount must be positive, got {absolute_min_amount}")

        self.alchemy_client = AlchemyClient.from_env()
        self.config = Config()
        self.portfolio_client = Portfolio.from_config(self.config)
        self.price_history_tool = GetAlchemyPriceHistoryByAddress(self.alchemy_client)
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

        super().__init__(model_id="anthropic/claude-3-5-sonnet-20241022", tools=tools)

    def get_trading_task(self) -> str:
        """
        Generate a trading task based on momentum signals and portfolio state.

        Combines momentum analysis, portfolio balance, and trading requirements into
        a structured prompt for intelligent trade evaluation.
        """
        # Get momentum signals
        momentum_signals = self.analyze_momentum_signals()
        if not momentum_signals:
            return ""

        # Get portfolio balance
        portfolio_info = self.get_portfolio_balance_info()

        # Construct user message
        task_prompt = (
            f"{portfolio_info}\n\n"
            f"{momentum_signals}\n\n"
            "=== Trading Strategy Requirements ===\n"
            f"1. Allocate a maximum of {self.max_possible_percentage}% of existing {self.base_token} to any single trade\n"
            f"2. Prefer tokens with strongest combined momentum\n"
            f"3. Maintain a minimum of {self.absolute_min_amount} portfolio in {self.base_token}\n"
            "4. Consider price impact and liquidity\n\n"
            "Please decide whether to trade strictly based on the above information and requirements.\n"
            "You are able to buy or sell based on the momentum signals you receive,\n"
            "where selling means swapping an alerted token for the base token.\n"
            "If you decide to trade, determine how much you want to trade for which token.\n"
            "Provide your reasonings before making the final decision."
        )

        return task_prompt

    def get_portfolio_balance_info(self) -> str:
        """
        Generate formatted portfolio balance information.

        Returns a string containing a CSV-formatted summary of current token balances
        with timestamp for trade analysis.
        """
        portfolio_balance = self.portfolio_client.get_token_balances(chain=self.chain)
        timestamp = portfolio_balance.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        tokens = portfolio_balance.get_non_zero_balances()
        balance_info = [
            f"=== Portfolio Balance Summary at {timestamp} ===",
            "```csv",
            "symbol,address,amount",
            *[f"{token.token_info.symbol},{token.token_info.address},{token.value}" for token in tokens],
            "```",
        ]
        logging.debug("Portfolio Balance retrieved")
        return "\n".join(balance_info)

    def analyze_momentum_signals(self) -> str:
        """
        Generate momentum signals for monitored tokens.

        Analyzes short and long-term price changes for each token,
        returning formatted signals when momentum thresholds are met.
        """
        signals = []
        for address in self.token_addresses:
            logging.info(f"Getting price history for {address}")

            price_history = self.price_history_tool.forward(
                address=address,
                chain=self.chain,
                interval="5m",
                history=1,  # 1 day of history
            )

            prices = [price.value for price in price_history.data]
            price_changes = PriceChanges.from_prices(
                prices, short_period=self.short_term_periods, long_period=self.long_term_periods
            )

            # Check if price changes meet thresholds
            momentum_signal = price_changes.is_above_threshold(self.short_term_threshold, self.long_term_threshold)

            # Log all signals for monitoring
            logging.info(f"{self.short_term_periods * 5} minute change: {price_changes.short_term:.2f}%")
            logging.info(f"{self.long_term_periods * 5} minute change: {price_changes.long_term:.2f}%")

            # Only generate trade instructions for positive momentum
            if momentum_signal:
                signals.append(self.format_signal_message(address, price_changes.short_term, price_changes.long_term))
        if not signals:
            return ""
        signals_str = "\n".join(signals)
        return f"=== Momentum Trade Signals ===\n{signals_str}"

    def format_signal_message(self, address: str, short_term_change: Decimal, long_term_change: Decimal) -> str:
        """Helper to format momentum signal message with timestamp."""
        direction = "Upward" if short_term_change > 0 else "Downward"
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        momentum_str = f"{direction} momentum at {timestamp} detected for {address}:\n"
        logging.info(momentum_str)

        return (
            f"{momentum_str}"
            f"  - {self.short_term_periods * 5}min change: {short_term_change:.2f}%\n"
            f"  - {self.long_term_periods * 5}min change: {long_term_change:.2f}%\n"
        )


async def main() -> None:
    # Load environment variables
    dotenv.load_dotenv()

    # Configure logging
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )

    # Define the tokens (in addition to the base token) to monitor
    token_addresses = [
        "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825",  # AIXBT
        "0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b",  # VIRTUAL
        "0x731814e491571A2e9eE3c5b1F7f3b962eE8f4870",  # VADER
    ]

    # Initialize the agent
    agent = PriceMomentumCronAgent(
        token_addresses=token_addresses,
        chain="base",
        short_term_minutes=5,
        short_term_threshold=0.1,
        long_term_minutes=60,
        long_term_threshold=0.5,
    )

    # Initialize the cron client
    cron_client = CronJobClient(
        agent=agent,
        client_id="Price Momentum Cron Agent With Portfolio Balance",
        interval_seconds=300,  # 5 minutes
        response_handler=lambda _: None,
        message_generator=agent.get_trading_task,
        max_history=2,  # Last message pair only
    )

    # Start the cron client
    await asyncio.gather(cron_client.start())


if __name__ == "__main__":
    asyncio.run(main())
