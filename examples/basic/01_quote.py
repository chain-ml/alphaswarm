from typing import Dict, List

import dotenv
import yaml
from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.config import Config
from alphaswarm.core.tool import AlphaSwarmToolBase
from alphaswarm.tools.exchanges.get_token_price import GetTokenPrice

dotenv.load_dotenv()
config = Config()

# Initialize tools
tools: List[AlphaSwarmToolBase] = [
    GetTokenPrice(config),  # Get the price of a token pair from available DEXes
]

# Create the agent
token_addresses: Dict[str, str] = config.get_chain_config("base").get_token_address_mapping()
hints = "Here are token addresses: \n" + yaml.dump(token_addresses)  # So agent knows addresses to query
agent = AlphaSwarmAgent(tools=tools, model_id="anthropic/claude-3-5-sonnet-20241022", hints=hints)


# Interact with the agent
async def main() -> None:
    response = await agent.process_message("What's the current price of AIXBT in USDC on Base for Uniswap v3?")
    print(response)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
