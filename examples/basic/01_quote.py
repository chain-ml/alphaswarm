from typing import List

import dotenv
from alphaswarm.agent import AlphaSwarmAgent
from alphaswarm.config import Config
from alphaswarm.core.tool import AlphaSwarmToolBase
from alphaswarm.tools.core import GetTokenAddress
from alphaswarm.tools.exchanges import GetTokenPrice

dotenv.load_dotenv()
config = Config()

# Initialize tools
tools: List[AlphaSwarmToolBase] = [
    GetTokenAddress(config),  # Get token address from a symbol
    GetTokenPrice(config),  # Get the price of a token pair from available DEXes given addresses
]

# Create the agent
token_addresses: Dict[str, str] = config.get_chain_config("base").get_token_address_mapping()
hints = "Here are token addresses: \n" + yaml.dump(token_addresses)  # So agent knows addresses to query

# Get LLM config for Anthropic
llm_config = config.get_default_llm_config("anthropic")
agent = AlphaSwarmAgent(tools=tools, model_id=llm_config.model_id, hints=hints)


# Interact with the agent
async def main() -> None:
    response = await agent.process_message("What's the current price of AIXBT in USDC on Base for Uniswap v3?")
    print(response)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
