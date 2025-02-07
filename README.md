# AlphaSwarm

AlphaSwarm is a starter kit for building LLM-powered AI agents that interpret natural language trading strategies, analyze real-time market signals, and autonomously execute trades across multiple chains.

## Features

### AI-Powered Trading with Agents
- 🤖 LLM-powered agents capable of processing complex, unstructured signals for trading decisions
- 🧠 Intelligent tool selection and chaining for complex multi-step analysis
- 🚀 Dynamic composition and execution of Python code using available tools
- 💬 Natural language strategy definition and real-time reasoning
- 📊 Iterative agentic reasoning to evaluate market conditions, weigh multiple input signals, and make trading decisions given input trading strategy

### Trading & Execution
- ⚡ Real-time strategy execution and monitoring
- 🔔 Flexible execution modes:
  - Automated trading alerts via Telegram
  - Autonomous trade execution
- 🔄 Multi-chain support with growing DEX integrations:
  - Ethereum, Base, Coming Soon: Solana 
  - Uniswap V2/V3, Coming Soon: Jupiter

### Modular Architecture
- 🛠️ Extensible plugin system for:
  - Data sources and signals
  - Trading strategies
  - Agent tools and capabilities
  - DEX integrations
  - On-chain data providers
- 🔌 Easy integration of new data sources and execution venues

### Roadmap
- 🌐 Integration with Theoriq protocol to connect with growing ecosystem of agents and swarms providing trading strategies and signals

## Prerequisites

- Python 3.11 or higher
- Poetry (package manager)
- Basic understanding of crypto trading concepts

## Getting Started

### 1. Installation

First, ensure you have all prerequisites installed:
- Python 3.11 or higher
- Poetry (package manager)
- Basic understanding of crypto trading concepts

Then follow these steps:

1. Clone the repository:
```bash
git clone https://github.com/chain-ml/alphaswarm.git
cd alphaswarm
```

2. Install Poetry if you haven't already:
```bash
pipx install poetry
```

3. Install dependencies:
```bash
# For basic installation
poetry install

# For development (includes testing tools)
poetry install --with dev
```

Note: Poetry manages its own virtual environments, so a separate virtual environment should not be required. Refer to the [Poetry documentation](https://python-poetry.org/docs/managing-environments/) for more information.

### 2. API Keys Setup

Before running the framework, you'll need to obtain several API keys:

1. **LLM API Key** (at least one required):
   - [OpenAI API Key](https://platform.openai.com/) or
   - [Anthropic API Key](https://www.anthropic.com/)

2. **Blockchain Access**:
   - [Alchemy API Key](https://www.alchemy.com/) (required for blockchain data)
   - RPC URLs from [Alchemy](https://www.alchemy.com/) or [Infura](https://www.infura.io/) or another RPC provider of choice

3. **Optional - Telegram Bot** (for notifications):
   - Create a bot through [BotFather](https://t.me/botfather)
   - Get your chat ID by messaging `/id` to your bot

### 3. Environment Configuration

1. Create your environment file:
```bash
cp .env.example .env
```

2. Configure the required variables in your `.env` file.

#### Required environment variables:

LLM Configuration (at least one required):
- `OPENAI_API_KEY`: Your OpenAI API key for using OpenAI models
- `ANTHROPIC_API_KEY`: Your Anthropic API key for using Claude models

Blockchain Access:
- `ALCHEMY_API_KEY`: Your Alchemy API key for accessing blockchain data

Ethereum Configuration (only if using Ethereum):
- `ETH_RPC_URL`: RPC endpoint URL for connecting to Ethereum network
- `ETH_WALLET_ADDRESS`: Your Ethereum wallet address for trading
- `ETH_PRIVATE_KEY`: Private key for your Ethereum wallet

Base Configuration (only if using Base):
- `BASE_RPC_URL`: RPC endpoint URL for connecting to Base network  
- `BASE_WALLET_ADDRESS`: Your Base wallet address for trading
- `BASE_PRIVATE_KEY`: Private key for your Base wallet

#### Optional configurations:

Testing environment variables:
- `ETH_SEPOLIA_RPC_URL`: Your Sepolia testnet RPC endpoint URL
- `ETH_SEPOLIA_WALLET_ADDRESS`: Your Ethereum wallet address for Sepolia testnet
- `ETH_SEPOLIA_PRIVATE_KEY`: Private key for your Sepolia testnet wallet

Notification settings:
- `TELEGRAM_BOT_TOKEN`: Required for sending alerts via Telegram bot
- `TELEGRAM_CHAT_ID`: Required chat ID for receiving Telegram alerts
- `TELEGRAM_SERVER_IP`: IP address for Telegram server (defaults to 0.0.0.0)
- `TELEGRAM_SERVER_PORT`: Port for Telegram server (defaults to 8000)

Logging configuration:
- `LOG_LEVEL`: Sets logging verbosity level (defaults to INFO)
- `LOG_FORMAT`: Custom format for log messages (default: "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

#### Security Notes

- Never commit your `.env` file to version control
- Keep private keys secure and start with testnets
- Use separate API keys for development and production
- Consider using key rotation for production deployments

### 4. Additional Configuration

The framework uses YAML configuration files to define trading venues, token pairs, and other application-specific and trading-related settings. The main configuration file is `config/default.yaml`.

Key configuration sections:
- **LLM Configuration**: Model settings, provider details, and parameters
- **Network Environments**: Production and test network configurations
- **Trading Venues**: Supported DEXs with their supported pairs and settings for each chain
- **Chain Configuration**: 
  - Chain-specific wallet and RPC settings
  - Token addresses and decimals
  - Gas settings and transaction parameters
- **Telegram**: Bot configuration for notifications

Note: Always verify contract addresses from official sources.

## Usage

### Quick Start

In all examples below, set your Anthropic API key in the `.env` file or change the model ID to an OpenAI model if using openAI.

#### Basic Example: Quote for a token pair

[Basic Example 01 - Quote](examples/basic_example_01_quote.py) is a first "hello world" example that:
- Initializes the Alphaswarm agent with a token price checking tool
- Uses Claude 3 Sonnet to process natural language queries
- Connects to Base network to fetch real-time token prices
- Demonstrates how to query token pair prices (AIXBT/USDC) using natural language

Run the example:
```bash
# Make sure you've configured your .env file first!
python examples/basic_example_01_quote.py
```

#### Basic Example: Execute a token swap

[Basic Example 02 - Swap](examples/basic_example_02_swap.py) is a follow up example that:
- Initializes the Alphaswarm agent with a token swap tool
- Uses Claude 3 Sonnet to process natural language queries
- Connects to Ethereum Sepolia network to execute a token swap
- Demonstrates how to initiate a token swap (3 USDC for WETH) using natural language

Run the example:
```bash
# Make sure you've configured your .env file first!
python examples/basic_example_02_swap.py
```

#### Strategy Example: Check trading strategy and optionally execute it

[Basic Example 03 - Strategy](examples/basic_example_03_strategy.py) dives into the optional execution of a trading strategy given input signals that:
- Initializes the Alphaswarm agent with both strategy analysis and token swap tools
- Uses Claude 3 Sonnet to process natural language queries
- Defines a simple trading strategy: Swap 3 USDC for WETH on Ethereum Sepolia when price below 10000 USDC per WETH
- Evaluates the trading strategy conditions using real-time market data when triggered
- Conditionally executes trades only when strategy conditions are met

Run the example:
```bash
# Make sure you've configured your .env file first!
python examples/basic_example_03_strategy.py
```

### More Examples

Check out the `examples/` directory for more complete examples:
- `examples/terminal.py` - Command-line interface usage
- `examples/telegram_bot.py` - Setting up Telegram notifications
- `examples/cron.py` - Running strategies on a schedule

## Development

### Running Tests
```bash
poetry run pytest
```

### Code Quality
```bash
# Format code
poetry run black .
poetry run isort .

# Run linters
poetry run ruff check .
poetry run mypy .
```

or use Makefile shortcuts:
```bash
make dev-lint
```

## Security

For security concerns, please review our [Security Policy](SECURITY.md). We take all security issues seriously.

## Support

Need help? Check out our [Support Guide](SUPPORT.md) for ways to get assistance.

## Contributing

Alphaswarm is a project under active development. We welcome all contributions, pull requests, feature requests or reported issues.

## Disclaimer

**IMPORTANT LEGAL NOTICE AND RISK DISCLOSURE**

AlphaSwarm is experimental software in active development. All features, tools, and capabilities should be considered experimental and used with appropriate caution.

By using AlphaSwarm, you acknowledge and agree that:

1. **Experimental Nature**: The software utilizes experimental technologies, including Large Language Models (LLMs), which are inherently non-deterministic and may produce unpredictable results.

2. **Financial Risk**: Any trading or investment activities carry significant risk. Crypto markets are highly volatile and trading decisions, whether manual or automated, can result in partial or complete loss of funds.

3. **No Financial Advice**: Nothing in this software constitutes financial, investment, legal, or tax advice. All trading strategies, examples, and code snippets are for illustrative purposes only.

4. **User Responsibility**: Users are solely responsible for:
   - Understanding the risks involved
   - Conducting their own due diligence
   - Securing their private keys and funds
   - Testing thoroughly on testnets before using real funds
   - Setting appropriate risk management parameters

5. **No Warranty**: The software is provided "AS IS", without warranty of any kind, express or implied. The developers and contributors:
   - Make no representations about its suitability for any purpose
   - Take no responsibility for any financial losses incurred
   - Do not guarantee the accuracy or reliability of any trading signals or decisions

6. **Limitation of Liability**: Under no circumstances shall the developers, contributors, or associated entities be liable for any direct, indirect, incidental, special, exemplary, or consequential damages arising from the use of this software.

USE OF THIS SOFTWARE FOR TRADING WITH REAL FUNDS SHOULD ONLY BE DONE WITH EXTREME CAUTION AND AFTER THOROUGHLY UNDERSTANDING THE RISKS AND LIMITATIONS INVOLVED.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

