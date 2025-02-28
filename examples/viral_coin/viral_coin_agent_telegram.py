#!/usr/bin/env python3
"""Telegram bot for the Viral Coin Agent."""

import asyncio
import logging
import os
import re
import sys
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union

import dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from alphaswarm.agents.viral_coin.viral_coin_agent import ViralCoinAgent, ViralCoinMetrics
from alphaswarm.config import Config


# Conversation states
CHAIN, MARKET_CAP, AGE, DEPTH, CONFIRM, BUY_CONFIRM, BUY_AMOUNT, DCA_CONFIRM, DCA_AMOUNT, DCA_INTERVALS = range(10)


class ViralCoinTelegramBot:
    """Telegram bot for the Viral Coin Agent."""

    def __init__(self) -> None:
        """Initialize the Telegram bot."""
        # Load environment variables
        dotenv.load_dotenv()
        
        # Configure logging
        logging.basicConfig(
            format="%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            level=logging.INFO,
        )
        
        # Get Telegram bot token
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
        
        # Initialize the agent
        self.config = Config()
        llm_config = self.config.get_default_llm_config("anthropic")
        
        self.agent = ViralCoinAgent(
            model_id=llm_config.model_id,
            chain="ethereum_sepolia",  # Default chain
            telegram_enabled=True,
        )
        
        # Initialize the application
        self.application = Application.builder().token(self.token).build()
        
        # Add conversation handler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states={
                CHAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.chain)],
                MARKET_CAP: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.market_cap)],
                AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.age)],
                DEPTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.depth)],
                CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.confirm)],
                BUY_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.buy_confirm)],
                BUY_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.buy_amount)],
                DCA_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.dca_confirm)],
                DCA_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.dca_amount)],
                DCA_INTERVALS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.dca_intervals)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )
        
        self.application.add_handler(conv_handler)
        
        # Add command handlers
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("report", self.report_command))
        self.application.add_handler(CommandHandler("buy", self.buy_command))
        self.application.add_handler(CommandHandler("dca", self.dca_command))
        
        # Add error handler
        self.application.add_error_handler(self.error_handler)
        
        # Logger
        self.logger = logging.getLogger(__name__)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start the conversation and ask for the chain."""
        user = update.effective_user
        await update.message.reply_text(
            f"Hello {user.first_name}! I'm the Viral Coin Agent. "
            "I can help you find the most viral cryptocurrencies based on social metrics.\n\n"
            "Let's set up a search. First, which chain would you like to use?\n\n"
            "Options: ethereum_sepolia (test), ethereum, base"
        )
        
        # Initialize user data
        context.user_data["search_params"] = {
            "chain": "ethereum_sepolia",
            "min_market_cap": 1000000,
            "max_age_days": 30,
            "search_depth": 50,
            "top_n": 10,
        }
        
        return CHAIN

    async def chain(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Store the chain and ask for the minimum market cap."""
        chain = update.message.text.strip().lower()
        
        # Validate chain
        valid_chains = ["ethereum_sepolia", "ethereum", "base"]
        if chain not in valid_chains:
            await update.message.reply_text(
                f"Invalid chain. Please choose from: {', '.join(valid_chains)}"
            )
            return CHAIN
        
        context.user_data["search_params"]["chain"] = chain
        
        await update.message.reply_text(
            "Great! Now, what's the minimum market cap (in USD) for coins to consider?\n\n"
            "Default: 1000000 ($1M)"
        )
        
        return MARKET_CAP

    async def market_cap(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Store the minimum market cap and ask for the maximum age."""
        try:
            min_market_cap = float(update.message.text.strip().replace(",", ""))
            if min_market_cap <= 0:
                raise ValueError("Market cap must be positive")
            
            context.user_data["search_params"]["min_market_cap"] = min_market_cap
            
            await update.message.reply_text(
                "What's the maximum age (in days) for coins to consider?\n\n"
                "Default: 30 days"
            )
            
            return AGE
        
        except ValueError:
            await update.message.reply_text(
                "Please enter a valid number for the minimum market cap."
            )
            return MARKET_CAP

    async def age(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Store the maximum age and ask for the search depth."""
        try:
            max_age_days = int(update.message.text.strip())
            if max_age_days <= 0:
                raise ValueError("Age must be positive")
            
            context.user_data["search_params"]["max_age_days"] = max_age_days
            
            await update.message.reply_text(
                "How many search results should I analyze per platform?\n\n"
                "Default: 50 results"
            )
            
            return DEPTH
        
        except ValueError:
            await update.message.reply_text(
                "Please enter a valid number for the maximum age."
            )
            return AGE

    async def depth(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Store the search depth and ask for confirmation."""
        try:
            search_depth = int(update.message.text.strip())
            if search_depth <= 0:
                raise ValueError("Search depth must be positive")
            
            context.user_data["search_params"]["search_depth"] = search_depth
            
            # Summarize the search parameters
            params = context.user_data["search_params"]
            await update.message.reply_text(
                "Here are your search parameters:\n\n"
                f"Chain: {params['chain']}\n"
                f"Minimum Market Cap: ${params['min_market_cap']:,}\n"
                f"Maximum Age: {params['max_age_days']} days\n"
                f"Search Depth: {params['search_depth']} results per platform\n\n"
                "Do you want to proceed with the search? (yes/no)"
            )
            
            return CONFIRM
        
        except ValueError:
            await update.message.reply_text(
                "Please enter a valid number for the search depth."
            )
            return DEPTH

    async def confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Confirm the search parameters and start the search."""
        response = update.message.text.strip().lower()
        
        if response in ["yes", "y"]:
            await update.message.reply_text(
                "Great! I'm starting the search for viral coins. This may take a few minutes..."
            )
            
            # Update agent parameters
            params = context.user_data["search_params"]
            self.agent.chain = params["chain"]
            self.agent.min_market_cap = params["min_market_cap"]
            self.agent.max_age_days = params["max_age_days"]
            self.agent.search_depth = params["search_depth"]
            
            try:
                # Find viral coins
                viral_coins = await self.agent.find_viral_coins()
                
                # Store the results
                context.user_data["viral_coins"] = viral_coins
                
                # Generate report
                report = await self.agent.generate_report(viral_coins, params["top_n"])
                
                # Send the report in chunks if it's too long
                if len(report) > 4000:
                    chunks = self._split_text(report, 4000)
                    for chunk in chunks:
                        await update.message.reply_text(chunk)
                else:
                    await update.message.reply_text(report)
                
                # Ask if the user wants to buy the top coin
                if viral_coins:
                    top_coin = viral_coins[0]
                    await update.message.reply_text(
                        f"Would you like to buy the top viral coin: {top_coin.coin_name} ({top_coin.coin_symbol})? (yes/no)"
                    )
                    return BUY_CONFIRM
                
                return ConversationHandler.END
            
            except Exception as e:
                self.logger.error(f"Error in search: {str(e)}")
                await update.message.reply_text(
                    f"An error occurred during the search: {str(e)}\n\n"
                    "Please try again with different parameters."
                )
                return ConversationHandler.END
        
        elif response in ["no", "n"]:
            await update.message.reply_text(
                "Search cancelled. You can start a new search with /start"
            )
            return ConversationHandler.END
        
        else:
            await update.message.reply_text(
                "Please answer with 'yes' or 'no'."
            )
            return CONFIRM

    async def buy_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Confirm buying the top viral coin."""
        response = update.message.text.strip().lower()
        
        if response in ["yes", "y"]:
            await update.message.reply_text(
                "How much would you like to buy? (in ETH)\n\n"
                "Example: 0.001"
            )
            return BUY_AMOUNT
        
        elif response in ["no", "n"]:
            await update.message.reply_text(
                "Would you like to set up DCA (Dollar Cost Averaging) buys for the top viral coin? (yes/no)"
            )
            return DCA_CONFIRM
        
        else:
            await update.message.reply_text(
                "Please answer with 'yes' or 'no'."
            )
            return BUY_CONFIRM

    async def buy_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Store the buy amount and execute the buy."""
        try:
            amount = update.message.text.strip()
            
            # Validate amount
            Decimal(amount)  # This will raise an exception if the amount is invalid
            
            await update.message.reply_text(
                f"Buying {amount} ETH worth of the top viral coin. Please wait..."
            )
            
            # Get the top coin
            viral_coins = context.user_data.get("viral_coins", [])
            if not viral_coins:
                await update.message.reply_text(
                    "No viral coins found. Please start a new search with /start"
                )
                return ConversationHandler.END
            
            top_coin = viral_coins[0]
            
            try:
                # Buy the coin
                result = await self.agent.buy_viral_coin(
                    coin_address=top_coin.address,
                    amount=amount,
                    slippage_percent=2.0,
                )
                
                # Send the result
                await update.message.reply_text(
                    f"🚨 **Viral Coin Purchase** 🚨\n\n"
                    f"Bought {amount} {self.agent._get_base_token_for_chain()} worth of "
                    f"{top_coin.coin_name} ({top_coin.coin_symbol})\n\n"
                    f"Transaction: {result.get('tx_hash', 'N/A')}"
                )
                
                # Ask if the user wants to set up DCA buys
                await update.message.reply_text(
                    "Would you like to set up DCA (Dollar Cost Averaging) buys for this coin? (yes/no)"
                )
                return DCA_CONFIRM
            
            except Exception as e:
                self.logger.error(f"Error buying coin: {str(e)}")
                await update.message.reply_text(
                    f"An error occurred during the purchase: {str(e)}"
                )
                return ConversationHandler.END
        
        except (ValueError, decimal.InvalidOperation):
            await update.message.reply_text(
                "Please enter a valid amount."
            )
            return BUY_AMOUNT

    async def dca_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Confirm setting up DCA buys."""
        response = update.message.text.strip().lower()
        
        if response in ["yes", "y"]:
            await update.message.reply_text(
                "What's the total amount you want to invest through DCA? (in ETH)\n\n"
                "Example: 0.01"
            )
            return DCA_AMOUNT
        
        elif response in ["no", "n"]:
            await update.message.reply_text(
                "Alright! You can start a new search with /start or get help with /help"
            )
            return ConversationHandler.END
        
        else:
            await update.message.reply_text(
                "Please answer with 'yes' or 'no'."
            )
            return DCA_CONFIRM

    async def dca_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Store the DCA amount and ask for the number of intervals."""
        try:
            amount = update.message.text.strip()
            
            # Validate amount
            Decimal(amount)  # This will raise an exception if the amount is invalid
            
            # Store the amount
            context.user_data["dca_amount"] = amount
            
            await update.message.reply_text(
                "How many intervals do you want to spread the buys over?\n\n"
                "Default: 7 intervals"
            )
            return DCA_INTERVALS
        
        except (ValueError, decimal.InvalidOperation):
            await update.message.reply_text(
                "Please enter a valid amount."
            )
            return DCA_AMOUNT

    async def dca_intervals(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Store the number of intervals and set up DCA buys."""
        try:
            intervals = int(update.message.text.strip())
            if intervals <= 0:
                raise ValueError("Number of intervals must be positive")
            
            await update.message.reply_text(
                f"Setting up DCA buys with {context.user_data['dca_amount']} ETH over {intervals} intervals. Please wait..."
            )
            
            # Get the top coin
            viral_coins = context.user_data.get("viral_coins", [])
            if not viral_coins:
                await update.message.reply_text(
                    "No viral coins found. Please start a new search with /start"
                )
                return ConversationHandler.END
            
            top_coin = viral_coins[0]
            
            try:
                # Set up DCA buys
                dca_result = await self.agent.setup_dca_buys(
                    coin_address=top_coin.address,
                    total_amount=context.user_data["dca_amount"],
                    num_intervals=intervals,
                    interval_hours=24,  # Default to daily
                    slippage_percent=2.0,
                )
                
                # Send the result
                await update.message.reply_text(
                    f"📊 **DCA Setup for Viral Coin** 📊\n\n"
                    f"Set up DCA buys for {top_coin.coin_name} ({top_coin.coin_symbol})\n\n"
                    f"Total Amount: {context.user_data['dca_amount']} {self.agent._get_base_token_for_chain()}\n"
                    f"Intervals: {intervals}\n"
                    f"Interval Hours: 24\n"
                    f"Schedule ID: {dca_result.get('id', 'N/A')}"
                )
                
                await update.message.reply_text(
                    "All done! You can start a new search with /start or get help with /help"
                )
                return ConversationHandler.END
            
            except Exception as e:
                self.logger.error(f"Error setting up DCA: {str(e)}")
                await update.message.reply_text(
                    f"An error occurred while setting up DCA: {str(e)}"
                )
                return ConversationHandler.END
        
        except ValueError:
            await update.message.reply_text(
                "Please enter a valid number for the intervals."
            )
            return DCA_INTERVALS

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel the conversation."""
        await update.message.reply_text(
            "Operation cancelled. You can start a new search with /start"
        )
        return ConversationHandler.END

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a message when the command /help is issued."""
        help_text = (
            "🚀 **Viral Coin Agent Help** 🚀\n\n"
            "I can help you find the most viral cryptocurrencies based on social metrics and allow you to trade them.\n\n"
            "**Commands:**\n"
            "/start - Start a new search for viral coins\n"
            "/report - Generate a report of the last search results\n"
            "/buy - Buy the top viral coin from the last search\n"
            "/dca - Set up DCA buys for the top viral coin\n"
            "/help - Show this help message\n"
            "/cancel - Cancel the current operation\n\n"
            "**How it works:**\n"
            "1. I search for mentions of cryptocurrencies on social media platforms\n"
            "2. I analyze the results to identify the most viral coins\n"
            "3. I generate a report of the top viral coins\n"
            "4. You can choose to buy the top viral coin or set up DCA buys\n\n"
            "**Supported chains:**\n"
            "- ethereum_sepolia (test)\n"
            "- ethereum\n"
            "- base"
        )
        
        await update.message.reply_text(help_text)

    async def report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Generate a report of the last search results."""
        viral_coins = context.user_data.get("viral_coins")
        
        if not viral_coins:
            await update.message.reply_text(
                "No viral coins found. Please start a new search with /start"
            )
            return
        
        await update.message.reply_text(
            "Generating report of the last search results..."
        )
        
        try:
            # Generate report
            report = await self.agent.generate_report(viral_coins, 10)
            
            # Send the report in chunks if it's too long
            if len(report) > 4000:
                chunks = self._split_text(report, 4000)
                for chunk in chunks:
                    await update.message.reply_text(chunk)
            else:
                await update.message.reply_text(report)
        
        except Exception as e:
            self.logger.error(f"Error generating report: {str(e)}")
            await update.message.reply_text(
                f"An error occurred while generating the report: {str(e)}"
            )

    async def buy_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Buy the top viral coin from the last search."""
        viral_coins = context.user_data.get("viral_coins")
        
        if not viral_coins:
            await update.message.reply_text(
                "No viral coins found. Please start a new search with /start"
            )
            return
        
        await update.message.reply_text(
            "How much would you like to buy? (in ETH)\n\n"
            "Example: 0.001"
        )
        
        # Set up a one-time conversation handler for the buy amount
        application = context.application
        
        async def buy_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            try:
                amount = update.message.text.strip()
                
                # Validate amount
                Decimal(amount)  # This will raise an exception if the amount is invalid
                
                await update.message.reply_text(
                    f"Buying {amount} ETH worth of the top viral coin. Please wait..."
                )
                
                top_coin = viral_coins[0]
                
                try:
                    # Buy the coin
                    result = await self.agent.buy_viral_coin(
                        coin_address=top_coin.address,
                        amount=amount,
                        slippage_percent=2.0,
                    )
                    
                    # Send the result
                    await update.message.reply_text(
                        f"🚨 **Viral Coin Purchase** 🚨\n\n"
                        f"Bought {amount} {self.agent._get_base_token_for_chain()} worth of "
                        f"{top_coin.coin_name} ({top_coin.coin_symbol})\n\n"
                        f"Transaction: {result.get('tx_hash', 'N/A')}"
                    )
                
                except Exception as e:
                    self.logger.error(f"Error buying coin: {str(e)}")
                    await update.message.reply_text(
                        f"An error occurred during the purchase: {str(e)}"
                    )
            
            except (ValueError, decimal.InvalidOperation):
                await update.message.reply_text(
                    "Please enter a valid amount."
                )
            
            # Remove the handler
            application.remove_handler(buy_handler)
        
        buy_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, buy_amount_handler)
        application.add_handler(buy_handler)

    async def dca_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Set up DCA buys for the top viral coin."""
        viral_coins = context.user_data.get("viral_coins")
        
        if not viral_coins:
            await update.message.reply_text(
                "No viral coins found. Please start a new search with /start"
            )
            return
        
        await update.message.reply_text(
            "What's the total amount you want to invest through DCA? (in ETH)\n\n"
            "Example: 0.01"
        )
        
        # Set up a conversation handler for DCA setup
        application = context.application
        
        async def dca_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            try:
                amount = update.message.text.strip()
                
                # Validate amount
                Decimal(amount)  # This will raise an exception if the amount is invalid
                
                # Store the amount
                context.user_data["dca_amount"] = amount
                
                await update.message.reply_text(
                    "How many intervals do you want to spread the buys over?\n\n"
                    "Default: 7 intervals"
                )
                
                # Remove this handler and add the intervals handler
                application.remove_handler(dca_amount_handler_obj)
                application.add_handler(dca_intervals_handler_obj)
            
            except (ValueError, decimal.InvalidOperation):
                await update.message.reply_text(
                    "Please enter a valid amount."
                )
        
        async def dca_intervals_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            try:
                intervals = int(update.message.text.strip())
                if intervals <= 0:
                    raise ValueError("Number of intervals must be positive")
                
                await update.message.reply_text(
                    f"Setting up DCA buys with {context.user_data['dca_amount']} ETH over {intervals} intervals. Please wait..."
                )
                
                top_coin = viral_coins[0]
                
                try:
                    # Set up DCA buys
                    dca_result = await self.agent.setup_dca_buys(
                        coin_address=top_coin.address,
                        total_amount=context.user_data["dca_amount"],
                        num_intervals=intervals,
                        interval_hours=24,  # Default to daily
                        slippage_percent=2.0,
                    )
                    
                    # Send the result
                    await update.message.reply_text(
                        f"📊 **DCA Setup for Viral Coin** 📊\n\n"
                        f"Set up DCA buys for {top_coin.coin_name} ({top_coin.coin_symbol})\n\n"
                        f"Total Amount: {context.user_data['dca_amount']} {self.agent._get_base_token_for_chain()}\n"
                        f"Intervals: {intervals}\n"
                        f"Interval Hours: 24\n"
                        f"Schedule ID: {dca_result.get('id', 'N/A')}"
                    )
                
                except Exception as e:
                    self.logger.error(f"Error setting up DCA: {str(e)}")
                    await update.message.reply_text(
                        f"An error occurred while setting up DCA: {str(e)}"
                    )
            
            except ValueError:
                await update.message.reply_text(
                    "Please enter a valid number for the intervals."
                )
            
            # Remove the handler
            application.remove_handler(dca_intervals_handler_obj)
        
        dca_amount_handler_obj = MessageHandler(filters.TEXT & ~filters.COMMAND, dca_amount_handler)
        dca_intervals_handler_obj = MessageHandler(filters.TEXT & ~filters.COMMAND, dca_intervals_handler)
        
        application.add_handler(dca_amount_handler_obj)

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors."""
        self.logger.error(f"Error: {context.error}")
        
        if update and isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                f"An error occurred: {context.error}"
            )

    def _split_text(self, text: str, max_length: int) -> List[str]:
        """Split text into chunks of maximum length."""
        chunks = []
        current_chunk = ""
        
        for line in text.split("\n"):
            if len(current_chunk) + len(line) + 1 <= max_length:
                current_chunk += line + "\n"
            else:
                chunks.append(current_chunk)
                current_chunk = line + "\n"
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks

    def run(self) -> None:
        """Run the bot."""
        self.application.run_polling()


def main() -> None:
    """Main function."""
    bot = ViralCoinTelegramBot()
    bot.run()


if __name__ == "__main__":
    main() 