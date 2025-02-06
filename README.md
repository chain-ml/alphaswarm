# AlphaSwarm

AlphaSwarm is a developer framework for autonomous crypto trading agents that leverages LLM-powered AI agents to process market signals and execute trading strategies. It enables both automated trading alerts and autonomous trading by analyzing on-chain data, social metrics, and market conditions in real-time.

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

2. Configure the required variables in your `.env` file:

```bash
# LLM Configuration (at least one required)
OPENAI_API_KEY=your_openai_key      # Required for OpenAI models
ANTHROPIC_API_KEY=your_anthropic_key # Required for Anthropic models

# Alchemy Configuration
ALCHEMY_API_KEY=your_alchemy_key    # Required for blockchain data access

# Chain Configuration
## Ethereum (only required if using Ethereum)
ETH_RPC_URL=your_ethereum_rpc       # Required for Ethereum trading
ETH_WALLET_ADDRESS=your_eth_address # Required for ETH trading
ETH_PRIVATE_KEY=your_eth_key       # Required for ETH trading

## Base (only required if using Base)
BASE_RPC_URL=your_base_rpc          # Required for Base trading
BASE_WALLET_ADDRESS=your_base_address # Required for Base trading
BASE_PRIVATE_KEY=your_base_key      # Required for Base trading      
```

3. Optional configurations:

```bash
# Testing
ETH_SEPOLIA_RPC_URL=your_sepolia_rpc  # For Ethereum testnet

# Notifications
TELEGRAM_BOT_TOKEN=your_bot_token      # Required for alerts
TELEGRAM_CHAT_ID=your_chat_id          # Required for alerts
TELEGRAM_SERVER_IP=0.0.0.0             # Default: 0.0.0.0
TELEGRAM_SERVER_PORT=8000              # Default: 8000

# Logging
LOG_LEVEL=INFO                         # Default: INFO
LOG_FORMAT="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

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

#### Basic Example

In a first "hello world" example we are going to get the price of a token pair from available DEXes on Base.
Set your Anthropic API key in the `.env` file or change the model ID to an OpenAI model if using openAI.

Create a new file or reference existing one `examples/basic_example_01_quote.py` in your project directory:

```python
import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.config import Config
from alphaswarm.tools.exchanges.get_token_price_tool import GetTokenPriceTool

dotenv.load_dotenv()
config = Config()

# Initialize tools
tools = [
    GetTokenPriceTool(config),  # Get the price of a token pair from available DEXes
]

# Create the agent
agent = AlphaSwarmAgent(tools=tools, model_id="anthropic/claude-3-5-sonnet-20241022")


# Interact with the agent
async def main():
    response = await agent.process_message("What's the current price of AIXBT in USDC on Base?")
    print(response)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
```

Run the example:
```bash
# Make sure you've configured your .env file first!
python examples/basic_example_01_quote.py
```

#### Follow-up Example: Execute a token swap

In a follow-up example we are going to execute a token swap on a supported DEX on Ethereum Sepolia.
Set your Anthropic API key in the `.env` file or change the model ID to an OpenAI model if using openAI.

Create a new file or reference existing one `examples/basic_example_02_swap.py`:

```python
import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.config import Config
from alphaswarm.tools.exchanges.execute_token_swap_tool import ExecuteTokenSwapTool

dotenv.load_dotenv()
config = Config(network_env="test")  # Use a testnet environment (as defined in config/default.yaml)

# Initialize tools
tools = [
    ExecuteTokenSwapTool(config),  # Execute a token swap on a supported DEX (Uniswap V2/V3 on Ethereum and Base chains)
]

# Create the agent
agent = AlphaSwarmAgent(tools=tools, model_id="anthropic/claude-3-5-sonnet-20241022")


# Interact with the agent
async def main():
    response = await agent.process_message("Swap 3 USDC for WETH on Ethereum Sepolia")
    print(response)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
```

Execute the token swap:
```bash
# Make sure you've configured your .env file first!
python examples/basic_example_02_swap.py
```

### Strategy Example: Check a trading strategy and optionally execute it

In a follow-up example we are going to check a trading strategy and optionally execute it.
Set your Anthropic API key in the `.env` file or change the model ID to an OpenAI model if using openAI.

Create a new file or reference existing one `examples/basic_example_03_strategy.py`:

```python
import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.config import Config
from alphaswarm.tools.exchanges.execute_token_swap_tool import ExecuteTokenSwapTool
from alphaswarm.tools.strategy_analysis.generic.generic_analysis import GenericStrategyAnalysisTool
from alphaswarm.tools.strategy_analysis.strategy import Strategy

dotenv.load_dotenv()
config = Config(network_env="test")  # Use a testnet environment (as defined in config/default.yaml)

# Initialize tools
strategy = Strategy(rules="Swap 3 USDC for WETH on Ethereum Sepolia when price below 10000 USDC per WETH", model_id="anthropic/claude-3-5-sonnet-20241022")

tools = [
    GenericStrategyAnalysisTool(strategy), # Check a trading strategy
    ExecuteTokenSwapTool(config),  # Execute a token swap on a supported DEX (Uniswap V2/V3 on Ethereum and Base chains)
]

# Create the agent
agent = AlphaSwarmAgent(tools=tools, model_id="anthropic/claude-3-5-sonnet-20241022")


# Interact with the agent
async def main():
    response = await agent.process_message("Check strategy and initiate a trade if applicable")
    print(response)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

```

Execute the token swap conditionally based on whether the strategy is applicable:
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

