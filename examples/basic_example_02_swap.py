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
agent = AlphaSwarmAgent(tools=tools, model_id="anthropic/claude-3-5-sonnet-latest")


# Interact with the agent
async def main():
    response = await agent.process_message("Swap 3 USDC for WETH on Ethereum Sepolia")
    print(response)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
