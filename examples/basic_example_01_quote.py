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
