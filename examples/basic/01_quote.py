import dotenv
from alphaswarm.agent import AlphaSwarmAgent
from alphaswarm.config import Config
from alphaswarm.tools import GetTokenAddress
from alphaswarm.tools.exchanges import GetTokenPriceTool

dotenv.load_dotenv()
config = Config()

# Initialize tools
tools = [
    GetTokenPriceTool(config),  # Get the price of a token pair from available DEXes given addresses
    GetTokenAddress(config),  # Get token address from a symbol
]

# Create the agent
agent = AlphaSwarmAgent(tools=tools, model_id="anthropic/claude-3-5-sonnet-20241022")


# Interact with the agent
async def main() -> None:
    response = await agent.process_message("What's the current price of AIXBT in USDC on Base for Uniswap v3?")
    print(response)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
