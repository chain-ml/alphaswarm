from typing import Dict

import dotenv
import yaml
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
token_addresses: Dict[str, str] = config.get_chain_config("ethereum_sepolia").get_token_address_mapping()
hints = "Here are token addresses: \n" + yaml.dump(token_addresses)  # So agent knows addresses to query
llm_config = config.get_llm_config()
agent = AlphaSwarmAgent(tools=tools, model_id=llm_config.model_id, hints=hints)

# Interact with the agent
async def main() -> None:
    response = await agent.process_message("Swap 3 USDC for WETH on Ethereum Sepolia")
    print(response)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
