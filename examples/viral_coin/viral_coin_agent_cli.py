#!/usr/bin/env python3
"""Command-line interface for the Viral Coin Agent."""

import argparse
import asyncio
import logging
import os
import sys
from decimal import Decimal
from typing import Any, Dict, Optional

import dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from alphaswarm.agents.viral_coin.viral_coin_agent import ViralCoinAgent
from alphaswarm.config import Config


async def run_viral_coin_agent(args: argparse.Namespace) -> None:
    """Run the viral coin agent with the provided arguments."""
    # Initialize the agent
    config = Config()
    llm_config = config.get_default_llm_config(args.model_provider)
    
    agent = ViralCoinAgent(
        model_id=llm_config.model_id,
        chain=args.chain,
        min_market_cap=args.min_market_cap,
        max_age_days=args.max_age_days,
        top_coins_limit=args.top_coins_limit,
        search_depth=args.search_depth,
        telegram_enabled=args.telegram,
        report_directory=args.report_dir,
    )
    
    # Find viral coins
    logging.info("Finding viral coins...")
    viral_coins = await agent.find_viral_coins()
    
    # Generate report
    logging.info("Generating report...")
    report = await agent.generate_report(viral_coins, args.top_n)
    print(report)
    
    # Initialize Telegram client if enabled
    if args.telegram:
        from alphaswarm.agent.clients import TelegramClient
        
        logging.info("Sending report to Telegram...")
        telegram_client = TelegramClient(
            agent=agent,
            client_id="Viral Coin Agent",
            response_handler=lambda response: logging.info(f"Telegram response: {response}"),
        )
        
        # Send report to Telegram
        await telegram_client.send_message(report)
    
    # Buy coins if requested
    if args.buy and viral_coins:
        top_coin = viral_coins[0]
        logging.info(f"Buying top viral coin: {top_coin.coin_name} ({top_coin.coin_symbol})")
        
        # Buy the coin
        result = await agent.buy_viral_coin(
            coin_address=top_coin.address,
            amount=args.buy_amount,
            slippage_percent=args.slippage,
        )
        
        logging.info(f"Buy result: {result}")
    
    # Set up DCA buys if requested
    if args.dca and viral_coins:
        top_coin = viral_coins[0]
        logging.info(f"Setting up DCA buys for: {top_coin.coin_name} ({top_coin.coin_symbol})")
        
        # Set up DCA buys
        dca_result = await agent.setup_dca_buys(
            coin_address=top_coin.address,
            total_amount=args.dca_amount,
            num_intervals=args.dca_intervals,
            interval_hours=args.dca_interval_hours,
            slippage_percent=args.slippage,
        )
        
        logging.info(f"DCA setup result: {dca_result}")


def main() -> None:
    """Main entry point for the command-line interface."""
    # Load environment variables
    dotenv.load_dotenv()
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Viral Coin Agent CLI")
    
    # General options
    parser.add_argument("--chain", type=str, default="ethereum_sepolia", help="Chain to use for trading")
    parser.add_argument("--model-provider", type=str, default="anthropic", choices=["anthropic", "openai"], help="LLM provider to use")
    parser.add_argument("--log-level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Logging level")
    parser.add_argument("--report-dir", type=str, default="reports/viral_coins", help="Directory to save reports")
    
    # Search options
    parser.add_argument("--min-market-cap", type=float, default=1000000, help="Minimum market cap for coins to consider")
    parser.add_argument("--max-age-days", type=int, default=30, help="Maximum age in days for coins to consider")
    parser.add_argument("--top-coins-limit", type=int, default=10, help="Number of top coins to search for")
    parser.add_argument("--search-depth", type=int, default=50, help="Number of search results to analyze per platform")
    parser.add_argument("--top-n", type=int, default=10, help="Number of top viral coins to include in the report")
    
    # Trading options
    parser.add_argument("--buy", action="store_true", help="Buy the top viral coin")
    parser.add_argument("--buy-amount", type=str, default="0.001", help="Amount to buy in base token (e.g., ETH)")
    parser.add_argument("--dca", action="store_true", help="Set up DCA buys for the top viral coin")
    parser.add_argument("--dca-amount", type=str, default="0.01", help="Total amount for DCA buys in base token (e.g., ETH)")
    parser.add_argument("--dca-intervals", type=int, default=7, help="Number of intervals for DCA buys")
    parser.add_argument("--dca-interval-hours", type=int, default=24, help="Hours between DCA buys")
    parser.add_argument("--slippage", type=float, default=2.0, help="Maximum slippage percentage")
    
    # Reporting options
    parser.add_argument("--telegram", action="store_true", help="Send report to Telegram")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=getattr(logging, args.log_level),
    )
    
    # Run the agent
    asyncio.run(run_viral_coin_agent(args))


if __name__ == "__main__":
    main() 