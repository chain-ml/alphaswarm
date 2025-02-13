import dotenv
from alphaswarm.agent import AlphaSwarmAgent
from alphaswarm.config import Config
from alphaswarm.tools import GetTokenAddress
from alphaswarm.tools.exchanges import ExecuteTokenSwapTool

dotenv.load_dotenv()
config = Config(network_env="test")  # Use a testnet environment (as defined in config/default.yaml)

# Initialize tools
tools = [
    ExecuteTokenSwapTool(config),  # Execute a token swap on a supported DEX
    GetTokenAddress(config),  # Get token address from a symbol
]

# Create the agent
agent = AlphaSwarmAgent(tools=tools, model_id="anthropic/claude-3-5-sonnet-20241022")


# Interact with the agent
async def main() -> None:
    response = await agent.process_message("Swap 3 USDC for WETH on Ethereum Sepolia")
    print(response)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
