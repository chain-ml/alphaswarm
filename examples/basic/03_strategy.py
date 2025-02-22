from typing import Dict, List

import dotenv
import yaml
from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.config import Config
from alphaswarm.core.tool import AlphaSwarmToolBase
from alphaswarm.tools.exchanges import ExecuteTokenSwap
from alphaswarm.tools.strategy_analysis import AnalyzeTradingStrategy, Strategy

dotenv.load_dotenv()
config = Config(network_env="test")  # Use a testnet environment (as defined in config/default.yaml)

# Initialize tools
strategy = Strategy(
    rules="Swap 3 USDC for WETH on Ethereum Sepolia when price below 10000 USDC per WETH",
    model_id="anthropic/claude-3-5-sonnet-20241022",
)

tools: List[AlphaSwarmToolBase] = [
    AnalyzeTradingStrategy(strategy),  # Check a trading strategy
    ExecuteTokenSwap(config),  # Execute a token swap on a supported DEX (Uniswap V2/V3 on Ethereum and Base chains)
]

# Create the agent
token_addresses: Dict[str, str] = config.get_chain_config("ethereum_sepolia").get_token_address_mapping()
hints = "Here are token addresses: \n" + yaml.dump(token_addresses)  # So agent knows addresses to query
llm_config = config.get_default_llm_config("anthropic")
agent = AlphaSwarmAgent(tools=tools, model_id=llm_config.model_id, hints=hints)

# Interact with the agent
async def main() -> None:
    response = await agent.process_message("Check strategy and initiate a trade if applicable")
    print(response)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
