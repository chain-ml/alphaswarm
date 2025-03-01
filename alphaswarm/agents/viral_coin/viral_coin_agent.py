"""Viral Coin Agent for AlphaSwarm."""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml
from pydantic import BaseModel, Field

from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.agent.clients import CronJobClient, TelegramClient
from alphaswarm.config import Config
from alphaswarm.services.alchemy import AlchemyClient
from alphaswarm.services.portfolio import Portfolio
from alphaswarm.tools.alchemy import GetAlchemyPriceHistoryByAddress
from alphaswarm.tools.core import GetTokenAddress
from alphaswarm.tools.exchanges import ExecuteTokenSwap, GetTokenPrice
from alphaswarm.tools.firecrawl import FirecrawlSearch, FirecrawlScrape


@dataclass
class CoinMention:
    """Represents a mention of a coin in social media or other platforms."""

    coin_symbol: str
    coin_name: str
    platform: str
    url: str
    mention_count: int
    sentiment_score: Optional[float] = None
    timestamp: datetime.datetime = datetime.datetime.now()


@dataclass
class ViralCoinMetrics:
    """Metrics for a viral coin."""

    coin_symbol: str
    coin_name: str
    address: str
    market_cap: float
    creation_date: Optional[datetime.datetime]
    total_mentions: int
    mentions_by_platform: Dict[str, int]
    sentiment_score: float
    volume_growth_24h: Optional[float] = None
    holder_growth_7d: Optional[float] = None
    price_volatility: Optional[float] = None
    developer_activity: Optional[float] = None
    virality_score: float = 0.0

    def calculate_virality_score(self, weights: Dict[str, float]) -> float:
        """Calculate the virality score based on the metrics and weights."""
        score = 0.0
        
        # Mentions score (normalized by total mentions)
        if self.total_mentions > 0:
            mentions_weight = weights.get("mentions", 0.4)
            score += mentions_weight * min(1.0, self.total_mentions / 100)
        
        # Sentiment score
        if self.sentiment_score is not None:
            sentiment_weight = weights.get("sentiment", 0.2)
            # Normalize sentiment from [-1, 1] to [0, 1]
            normalized_sentiment = (self.sentiment_score + 1) / 2
            score += sentiment_weight * normalized_sentiment
        
        # Volume growth score
        if self.volume_growth_24h is not None:
            volume_weight = weights.get("volume_growth", 0.15)
            # Normalize volume growth (cap at 100%)
            normalized_volume = min(1.0, max(0.0, self.volume_growth_24h / 100))
            score += volume_weight * normalized_volume
        
        # Holder growth score
        if self.holder_growth_7d is not None:
            holder_weight = weights.get("holder_growth", 0.15)
            # Normalize holder growth (cap at 100%)
            normalized_holder = min(1.0, max(0.0, self.holder_growth_7d / 100))
            score += holder_weight * normalized_holder
        
        # Price volatility score
        if self.price_volatility is not None:
            volatility_weight = weights.get("price_volatility", 0.05)
            # Normalize volatility (cap at 50%)
            normalized_volatility = min(1.0, max(0.0, self.price_volatility / 50))
            score += volatility_weight * normalized_volatility
        
        # Developer activity score
        if self.developer_activity is not None:
            dev_weight = weights.get("developer_activity", 0.05)
            # Normalize developer activity (cap at 50 commits)
            normalized_dev = min(1.0, max(0.0, self.developer_activity / 50))
            score += dev_weight * normalized_dev
        
        self.virality_score = score
        return score


class ViralCoinReport(BaseModel):
    """Report for viral coins."""

    timestamp: str
    top_coins: List[Dict[str, Any]]
    search_parameters: Dict[str, Any]
    network: str
    report_id: str


class ViralCoinAgent(AlphaSwarmAgent):
    """
    An agent that finds the most viral coins based on social metrics and allows trading.
    
    The agent uses Firecrawl to search for mentions of coins on social media platforms,
    analyzes the results to identify the most viral coins, and allows trading based on
    user-defined parameters.
    """

    def __init__(
        self,
        model_id: str,
        config_path: Optional[str] = None,
        chain: str = "ethereum_sepolia",
        min_market_cap: float = 1000000,  # $1M
        max_age_days: int = 30,
        top_coins_limit: int = 100,
        search_depth: int = 50,
        telegram_enabled: bool = True,
        report_directory: str = "reports/viral_coins",
    ) -> None:
        """
        Initialize the ViralCoinAgent.
        
        Args:
            model_id: ID of the LLM model to use
            config_path: Path to the configuration file
            chain: Chain to use for trading
            min_market_cap: Minimum market cap for coins to consider
            max_age_days: Maximum age in days for coins to consider
            top_coins_limit: Number of top coins to search for
            search_depth: Number of search results to analyze per platform
            telegram_enabled: Whether to enable Telegram reporting
            report_directory: Directory to save reports
        """
        self.config = Config()
        self.alchemy_client = AlchemyClient.from_env()
        self.portfolio_client = Portfolio.from_config(self.config)
        
        # Load agent configuration
        self.agent_config = self._load_config(config_path)
        
        # Set parameters
        self.chain = chain
        self.min_market_cap = min_market_cap
        self.max_age_days = max_age_days
        self.top_coins_limit = top_coins_limit
        self.search_depth = search_depth
        self.telegram_enabled = telegram_enabled
        self.report_directory = report_directory
        
        # Ensure report directory exists
        os.makedirs(self.report_directory, exist_ok=True)
        
        # Initialize tools
        tools = [
            GetTokenAddress(config=self.config),
            GetTokenPrice(config=self.config),
            ExecuteTokenSwap(config=self.config),
            GetAlchemyPriceHistoryByAddress(self.alchemy_client),
            FirecrawlSearch(config=self.config),
            FirecrawlScrape(config=self.config),
        ]
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        
        super().__init__(model_id=model_id, tools=tools)

    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load the agent configuration from a YAML file."""
        if config_path is None:
            config_path = os.path.join("config", "viral_coin_agent.yaml")
        
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
                return config.get("viral_coin_agent", {})
        except Exception as e:
            self.logger.error(f"Error loading configuration: {str(e)}")
            return {}

    async def find_viral_coins(
        self,
        min_market_cap: Optional[float] = None,
        max_age_days: Optional[int] = None,
        top_coins_limit: Optional[int] = None,
        search_depth: Optional[int] = None,
    ) -> List[ViralCoinMetrics]:
        """
        Find the most viral coins based on social metrics.
        
        Args:
            min_market_cap: Minimum market cap for coins to consider
            max_age_days: Maximum age in days for coins to consider
            top_coins_limit: Number of top coins to search for
            search_depth: Number of search results to analyze per platform
            
        Returns:
            List[ViralCoinMetrics]: List of viral coins with metrics
        """
        # Use provided parameters or defaults
        min_market_cap = min_market_cap or self.min_market_cap
        max_age_days = max_age_days or self.max_age_days
        top_coins_limit = top_coins_limit or self.top_coins_limit
        search_depth = search_depth or self.search_depth
        
        # Get the top coins from CoinGecko or similar API
        top_coins = await self._get_top_coins(min_market_cap, max_age_days, top_coins_limit)
        
        # Search for mentions of each coin on social platforms
        coin_metrics = []
        for coin in top_coins:
            metrics = await self._analyze_coin_virality(coin, search_depth)
            coin_metrics.append(metrics)
        
        # Sort coins by virality score
        coin_metrics.sort(key=lambda x: x.virality_score, reverse=True)
        
        return coin_metrics

    async def _get_top_coins(self, min_market_cap: float, max_age_days: int, limit: int) -> List[Dict[str, Any]]:
        """
        Get the top coins from CoinGecko or similar API.
        
        This is a placeholder implementation. In a real implementation, you would use
        a cryptocurrency API like CoinGecko to get the top coins.
        
        Args:
            min_market_cap: Minimum market cap for coins to consider
            max_age_days: Maximum age in days for coins to consider
            limit: Number of top coins to return
            
        Returns:
            List[Dict[str, Any]]: List of top coins
        """
        # This is a placeholder implementation
        # In a real implementation, you would use a cryptocurrency API
        
        # For testing purposes, we'll use a hardcoded list of coins
        # In a real implementation, you would fetch this data from an API
        
        # For Ethereum Sepolia testnet, we'll use the tokens from the config
        if self.chain == "ethereum_sepolia":
            tokens = self.config.chain_config.get("ethereum_sepolia", {}).get("tokens", {})
            coins = []
            for symbol, token_info in tokens.items():
                coins.append({
                    "symbol": symbol,
                    "name": symbol,
                    "address": token_info.get("address"),
                    "market_cap": 10000000,  # Placeholder
                    "creation_date": datetime.datetime.now() - datetime.timedelta(days=10),  # Placeholder
                })
            return coins[:limit]
        
        # For real networks, we would fetch data from an API
        # This is just a placeholder
        return []

    async def _analyze_coin_virality(self, coin: Dict[str, Any], search_depth: int) -> ViralCoinMetrics:
        """
        Analyze the virality of a coin based on social metrics.
        
        Args:
            coin: Coin information
            search_depth: Number of search results to analyze per platform
            
        Returns:
            ViralCoinMetrics: Metrics for the coin
        """
        symbol = coin["symbol"]
        name = coin["name"]
        address = coin["address"]
        
        # Get platforms to search from config
        platforms = [p["name"] for p in self.agent_config.get("virality_metrics", {}).get("platforms", [])]
        if not platforms:
            platforms = ["x.com", "reddit.com", "coingecko.com", "medium.com"]
        
        # Search for mentions of the coin on each platform
        firecrawl_search = FirecrawlSearch(config=self.config)
        mentions_by_platform = {}
        total_mentions = 0
        sentiment_scores = []
        
        for platform in platforms:
            # Generate search queries for the platform
            search_queries = self._generate_search_queries(symbol, name, platform)
            
            platform_mentions = 0
            for query in search_queries:
                try:
                    # Search for the coin on the platform
                    search_results = firecrawl_search.forward(
                        query=query,
                        platforms=[platform],
                        limit=search_depth,
                        extract_prompt=f"Extract all mentions of {symbol} or {name} cryptocurrency and analyze the sentiment (positive, negative, or neutral)"
                    )
                    
                    # Count mentions and analyze sentiment
                    platform_results = search_results.get(platform, [])
                    for result in platform_results:
                        content = result.content.get("markdown", "")
                        
                        # Count mentions
                        symbol_mentions = len(re.findall(rf'\b{re.escape(symbol)}\b', content, re.IGNORECASE))
                        name_mentions = len(re.findall(rf'\b{re.escape(name)}\b', content, re.IGNORECASE))
                        mentions = symbol_mentions + name_mentions
                        
                        platform_mentions += mentions
                        
                        # Analyze sentiment if we have JSON data
                        if "json" in result.content and result.content["json"]:
                            json_data = result.content["json"]
                            if isinstance(json_data, dict) and "sentiment" in json_data:
                                sentiment = json_data["sentiment"]
                                if isinstance(sentiment, str):
                                    # Convert sentiment string to score
                                    if sentiment.lower() == "positive":
                                        sentiment_scores.append(1.0)
                                    elif sentiment.lower() == "negative":
                                        sentiment_scores.append(-1.0)
                                    else:  # neutral
                                        sentiment_scores.append(0.0)
                                elif isinstance(sentiment, (int, float)):
                                    sentiment_scores.append(float(sentiment))
                
                except Exception as e:
                    self.logger.error(f"Error searching for {symbol} on {platform}: {str(e)}")
                    continue
            
            mentions_by_platform[platform] = platform_mentions
            total_mentions += platform_mentions
        
        # Calculate average sentiment score
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
        
        # Get additional metrics if available
        volume_growth_24h = None
        holder_growth_7d = None
        price_volatility = None
        developer_activity = None
        
        # Create metrics object
        metrics = ViralCoinMetrics(
            coin_symbol=symbol,
            coin_name=name,
            address=address,
            market_cap=coin["market_cap"],
            creation_date=coin.get("creation_date"),
            total_mentions=total_mentions,
            mentions_by_platform=mentions_by_platform,
            sentiment_score=avg_sentiment,
            volume_growth_24h=volume_growth_24h,
            holder_growth_7d=holder_growth_7d,
            price_volatility=price_volatility,
            developer_activity=developer_activity,
        )
        
        # Calculate virality score
        weights = {
            "mentions": 0.4,
            "sentiment": 0.2,
            "volume_growth": 0.15,
            "holder_growth": 0.15,
            "price_volatility": 0.05,
            "developer_activity": 0.05,
        }
        metrics.calculate_virality_score(weights)
        
        return metrics

    def _generate_search_queries(self, symbol: str, name: str, platform: str) -> List[str]:
        """
        Generate search queries for a coin on a platform.
        
        Args:
            symbol: Coin symbol
            name: Coin name
            platform: Platform to search on
            
        Returns:
            List[str]: List of search queries
        """
        # Get search terms for the platform from config
        platform_config = next(
            (p for p in self.agent_config.get("virality_metrics", {}).get("platforms", []) if p["name"] == platform),
            None
        )
        
        if platform_config and "search_terms" in platform_config:
            search_terms = platform_config["search_terms"]
            queries = [term.format(coin_symbol=symbol, coin_name=name) for term in search_terms]
        else:
            # Default search terms
            queries = [
                f"{symbol} crypto",
                f"{name} cryptocurrency",
                f"${symbol}",
            ]
        
        return queries

    async def generate_report(self, viral_coins: List[ViralCoinMetrics], top_n: int = 10) -> str:
        """
        Generate a report for the most viral coins.
        
        Args:
            viral_coins: List of viral coins with metrics
            top_n: Number of top coins to include in the report
            
        Returns:
            str: Report in markdown format
        """
        # Limit to top N coins
        top_coins = viral_coins[:min(top_n, len(viral_coins))]
        
        # Generate report
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        
        report = f"# Viral Coin Report\n\n"
        report += f"**Generated:** {timestamp}\n\n"
        report += f"**Network:** {self.chain}\n\n"
        report += f"**Search Parameters:**\n"
        report += f"- Minimum Market Cap: ${self.min_market_cap:,}\n"
        report += f"- Maximum Age: {self.max_age_days} days\n"
        report += f"- Top Coins Limit: {self.top_coins_limit}\n"
        report += f"- Search Depth: {self.search_depth} results per platform\n\n"
        
        report += f"## Top {len(top_coins)} Most Viral Coins\n\n"
        
        for i, coin in enumerate(top_coins):
            report += f"### {i+1}. {coin.coin_name} ({coin.coin_symbol})\n\n"
            report += f"**Address:** {coin.address}\n\n"
            report += f"**Virality Score:** {coin.virality_score:.2f}\n\n"
            report += f"**Total Mentions:** {coin.total_mentions}\n\n"
            
            report += "**Mentions by Platform:**\n\n"
            for platform, mentions in coin.mentions_by_platform.items():
                report += f"- {platform}: {mentions}\n"
            
            report += f"\n**Sentiment Score:** {coin.sentiment_score:.2f}\n\n"
            
            if coin.volume_growth_24h is not None:
                report += f"**24h Volume Growth:** {coin.volume_growth_24h:.2f}%\n\n"
            
            if coin.holder_growth_7d is not None:
                report += f"**7d Holder Growth:** {coin.holder_growth_7d:.2f}%\n\n"
            
            if coin.price_volatility is not None:
                report += f"**Price Volatility:** {coin.price_volatility:.2f}%\n\n"
            
            if coin.developer_activity is not None:
                report += f"**Developer Activity:** {coin.developer_activity:.2f}\n\n"
            
            report += "---\n\n"
        
        # Save report to file
        report_path = os.path.join(self.report_directory, f"viral_coin_report_{report_id}.md")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        with open(report_path, "w") as f:
            f.write(report)
        
        # Save report data as JSON
        report_data = ViralCoinReport(
            timestamp=timestamp,
            top_coins=[{
                "symbol": coin.coin_symbol,
                "name": coin.coin_name,
                "address": coin.address,
                "virality_score": coin.virality_score,
                "total_mentions": coin.total_mentions,
                "mentions_by_platform": coin.mentions_by_platform,
                "sentiment_score": coin.sentiment_score,
                "volume_growth_24h": coin.volume_growth_24h,
                "holder_growth_7d": coin.holder_growth_7d,
                "price_volatility": coin.price_volatility,
                "developer_activity": coin.developer_activity,
            } for coin in top_coins],
            search_parameters={
                "min_market_cap": self.min_market_cap,
                "max_age_days": self.max_age_days,
                "top_coins_limit": self.top_coins_limit,
                "search_depth": self.search_depth,
            },
            network=self.chain,
            report_id=report_id,
        )
        
        json_path = os.path.join(self.report_directory, f"viral_coin_report_{report_id}.json")
        
        with open(json_path, "w") as f:
            f.write(json.dumps(report_data.dict(), indent=2))
        
        return report

    async def buy_viral_coin(
        self,
        coin_address: str,
        amount: Union[float, str],
        slippage_percent: float = 2.0,
    ) -> Dict[str, Any]:
        """
        Buy a viral coin.
        
        Args:
            coin_address: Address of the coin to buy
            amount: Amount to buy in base token (e.g., ETH)
            slippage_percent: Maximum slippage percentage
            
        Returns:
            Dict[str, Any]: Transaction result
        """
        # Get base token for the chain
        base_token = self._get_base_token_for_chain()
        
        # Convert amount to Decimal if it's a string
        if isinstance(amount, str):
            amount = Decimal(amount)
        
        # Execute the swap
        swap_tool = ExecuteTokenSwap(config=self.config)
        result = swap_tool.forward(
            chain=self.chain,
            from_token=base_token,
            to_token=coin_address,
            amount=str(amount),
            slippage_bps=int(slippage_percent * 100),  # Convert percent to basis points
        )
        
        return result

    def _get_base_token_for_chain(self) -> str:
        """Get the base token symbol for the current chain."""
        if self.chain == "ethereum" or self.chain == "ethereum_sepolia":
            return "WETH"
        elif self.chain == "base":
            return "WETH"
        else:
            return "WETH"  # Default

    async def setup_dca_buys(
        self,
        coin_address: str,
        total_amount: Union[float, str],
        num_intervals: int = 7,
        interval_hours: int = 24,
        slippage_percent: float = 2.0,
    ) -> Dict[str, Any]:
        """
        Set up dollar-cost averaging (DCA) buys for a viral coin.
        
        Args:
            coin_address: Address of the coin to buy
            total_amount: Total amount to buy in base token (e.g., ETH)
            num_intervals: Number of intervals to spread the buys over
            interval_hours: Hours between each buy
            slippage_percent: Maximum slippage percentage
            
        Returns:
            Dict[str, Any]: DCA setup result
        """
        # Convert total_amount to Decimal if it's a string
        if isinstance(total_amount, str):
            total_amount = Decimal(total_amount)
        
        # Calculate amount per interval
        amount_per_interval = total_amount / Decimal(num_intervals)
        
        # Get base token for the chain
        base_token = self._get_base_token_for_chain()
        
        # Schedule the buys
        schedule = []
        for i in range(num_intervals):
            buy_time = datetime.datetime.now() + datetime.timedelta(hours=i * interval_hours)
            schedule.append({
                "interval": i + 1,
                "time": buy_time.strftime("%Y-%m-%d %H:%M:%S"),
                "amount": str(amount_per_interval),
                "from_token": base_token,
                "to_token": coin_address,
            })
        
        # Save the DCA schedule
        dca_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        dca_path = os.path.join(self.report_directory, f"dca_schedule_{dca_id}.json")
        
        dca_data = {
            "id": dca_id,
            "coin_address": coin_address,
            "total_amount": str(total_amount),
            "num_intervals": num_intervals,
            "interval_hours": interval_hours,
            "slippage_percent": slippage_percent,
            "chain": self.chain,
            "schedule": schedule,
        }
        
        with open(dca_path, "w") as f:
            f.write(json.dumps(dca_data, indent=2))
        
        return dca_data

    def get_trading_task(self) -> str:
        """
        Generate a trading task based on viral coin analysis.
        
        Returns:
            str: Trading task prompt
        """
        task_prompt = (
            "=== Viral Coin Analysis Task ===\n\n"
            "1. Find the most viral cryptocurrencies based on social media mentions and other metrics\n"
            "2. Generate a report of the top 10 most viral coins\n"
            "3. Recommend which coin to buy based on virality metrics\n\n"
            f"Parameters:\n"
            f"- Network: {self.chain}\n"
            f"- Minimum Market Cap: ${self.min_market_cap:,}\n"
            f"- Maximum Age: {self.max_age_days} days\n"
            f"- Search Depth: {self.search_depth} results per platform\n\n"
            "Please analyze the most viral cryptocurrencies and provide your recommendation."
        )
        
        return task_prompt


async def main() -> None:
    """Main function to run the viral coin agent."""
    # Configure logging
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )
    
    # Load environment variables
    import dotenv
    dotenv.load_dotenv()
    
    # Initialize the agent
    config = Config()
    llm_config = config.get_default_llm_config("anthropic")
    
    agent = ViralCoinAgent(
        model_id=llm_config.model_id,
        chain="ethereum_sepolia",
        min_market_cap=1000000,
        max_age_days=30,
        top_coins_limit=10,
        search_depth=50,
        telegram_enabled=True,
    )
    
    # Find viral coins
    viral_coins = await agent.find_viral_coins()
    
    # Generate report
    report = await agent.generate_report(viral_coins)
    print(report)
    
    # Initialize Telegram client if enabled
    if agent.telegram_enabled:
        telegram_client = TelegramClient(
            agent=agent,
            client_id="Viral Coin Agent",
            response_handler=lambda response: print(f"Telegram response: {response}"),
        )
        
        # Send report to Telegram
        await telegram_client.send_message(report)
    
    # Example of buying a viral coin
    if viral_coins:
        top_coin = viral_coins[0]
        print(f"Buying top viral coin: {top_coin.coin_name} ({top_coin.coin_symbol})")
        
        # Buy the coin
        result = await agent.buy_viral_coin(
            coin_address=top_coin.address,
            amount="0.001",  # Small amount for testing
            slippage_percent=2.0,
        )
        
        print(f"Buy result: {result}")
        
        # Set up DCA buys
        dca_result = await agent.setup_dca_buys(
            coin_address=top_coin.address,
            total_amount="0.01",
            num_intervals=7,
            interval_hours=24,
            slippage_percent=2.0,
        )
        
        print(f"DCA setup result: {dca_result}")


if __name__ == "__main__":
    asyncio.run(main()) 