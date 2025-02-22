# AlphaSwarm Examples

## Quick Start

> **Note**: In all examples below, set your Anthropic API key in the `.env` file or change the `model_id` to an OpenAI model (e.g. `gpt-4o`) if using OpenAI.

### Basic Example: Quote for a token pair

[Basic Example 01 - Quote](basic/01_quote.py) is a first "hello world" example that:
- Initializes the AlphaSwarm agent with a token price checking tool
- Uses Claude 3.5 Sonnet to process natural language queries
- Connects to Base network to fetch real-time token prices
- Demonstrates how to query token pair prices (AIXBT/USDC) using natural language

Run the example:
```bash
# cd alphaswarm/examples
# Make sure you've configured your .env file first!
python basic/01_quote.py
```

### Basic Example: Execute a token swap

[Basic Example 02 - Swap](basic/02_swap.py) is a follow-up example that:
- Initializes the AlphaSwarm agent with a token swap tool
- Uses Claude 3.5 Sonnet to process natural language queries
- Connects to Ethereum Sepolia network to execute a token swap
- Demonstrates how to initiate a token swap (3 USDC for WETH) using natural language

Run the example:
```bash
# cd alphaswarm/examples
# Make sure you've configured your .env file first!
python basic/02_swap.py
```

### Strategy Example: Check trading strategy and optionally execute it

[Basic Example 03 - Strategy](basic/03_strategy.py) dives into the optional execution of a trading strategy given input signals that:
- Initializes the AlphaSwarm agent with both strategy analysis and token swap tools
- Uses Claude 3.5 Sonnet to process natural language queries
- Defines a simple trading strategy: Swap 3 USDC for WETH on Ethereum Sepolia when price below 10000 USDC per WETH
- Evaluates the trading strategy conditions using real-time market data when triggered
- Conditionally executes trades only when strategy conditions are met

Run the example:
```bash
# cd alphaswarm/examples
# Make sure you've configured your .env file first!
python basic/03_strategy.py
```

### Agent Example: Make trading decisions based on price momentum signals and portfolio balances

[Portfolio Price Momentum Agent Example](agents/portfolio_price_momentum_cron.py) demonstrates a more sophisticated trading agent that:
- Implements a portfolio-aware momentum trading strategy using AlphaSwarm's agent framework
- Monitors multiple token prices on a schedule using Alchemy's price feed from a CronJobClient
- Evaluates both short-term (e.g. 5min) and long-term (e.g. 60min) price momentum signals to assess directional alignment (upward for buying or downward for selling)
- Makes a dynamic trading decision based on the above signals and the current token balances in the portfolio
- Additionally, the agent can be configured to limit individual trade sizes and maintain a minimum balance in your base token

Run the example:
```bash
# cd alphaswarm/examples
# Make sure you've configured your .env file first!
python agents/portfolio_price_momentum_cron.py
```

## More Examples

Check out the `interaction/` directory for more complete examples:
- [Command-line interface usage](interaction/terminal.py)
- [Setting up Telegram bot](interaction/telegram_bot.py)
- [Running strategies on a schedule](interaction/cron.py)
