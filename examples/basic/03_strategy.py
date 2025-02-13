import dotenv
from alphaswarm.agent import AlphaSwarmAgent
from alphaswarm.config import Config
from alphaswarm.tools import GetTokenAddress
from alphaswarm.tools.exchanges import ExecuteTokenSwapTool, GetTokenPriceTool
from alphaswarm.tools.strategy_analysis import GenericStrategyAnalysisTool, Strategy

dotenv.load_dotenv()
config = Config(network_env="test")  # Use a testnet environment (as defined in config/default.yaml)

# Initialize tools
strategy = Strategy(
    rules="Swap 3 USDC for WETH on Ethereum Sepolia when price below 10_000 USDC per WETH",
    model_id="anthropic/claude-3-5-sonnet-20241022",
)

tools = [
    GetTokenPriceTool(config),  # Get the price of a token pair from available DEXes given addresses
    GetTokenAddress(config),  # Get token address from a symbol
    GenericStrategyAnalysisTool(strategy),  # Check a trading strategy
    ExecuteTokenSwapTool(config),  # Execute a token swap on a supported DEX
]

# Create the agent
agent = AlphaSwarmAgent(tools=tools, model_id="anthropic/claude-3-5-sonnet-20241022")


# Interact with the agent
async def main() -> None:
    response = await agent.process_message("Check strategy and initiate a trade if applicable")
    print(response)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
