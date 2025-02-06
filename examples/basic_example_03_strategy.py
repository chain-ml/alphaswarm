import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.config import Config
from alphaswarm.tools.exchanges.execute_token_swap_tool import ExecuteTokenSwapTool
from alphaswarm.tools.strategy_analysis.generic.generic_analysis import GenericStrategyAnalysisTool
from alphaswarm.tools.strategy_analysis.strategy import Strategy

dotenv.load_dotenv()
config = Config(network_env="test")  # Use a testnet environment (as defined in config/default.yaml)

# Initialize tools
strategy = Strategy(
    rules="Swap 3 USDC for WETH on Ethereum Sepolia when price below 10000 USDC per WETH",
    model_id="anthropic/claude-3-5-sonnet-20241022",
)

tools = [
    GenericStrategyAnalysisTool(strategy),  # Check a trading strategy
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
