import asyncio
import json
from typing import List

import dotenv
from alphaswarm.agent.agent import AlphaSwarmAgent
from alphaswarm.agent.clients import TerminalClient
from alphaswarm.config import BASE_PATH, Config
from alphaswarm.tools.telegram import SendTelegramNotificationTool
from lab.trade_advisor_agent.tools import CallForecastingAgentTool
from smolagents import Tool


async def main() -> None:
    dotenv.load_dotenv()
    config = Config()

    telegram_config = config.get("telegram", {})
    telegram_bot_token = telegram_config.get("bot_token")
    chat_id = int(telegram_config.get("chat_id"))

    tools: List[Tool] = [
        SendTelegramNotificationTool(telegram_bot_token=telegram_bot_token, chat_id=chat_id),
        CallForecastingAgentTool(),
    ]  # Add your tools here

    my_tokens = {
        "AIXBT (base)": "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825",
        "VIRTUAL (base)": "0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b",
        "VADER (base)": "0x731814e491571A2e9eE3c5b1F7f3b962eE8f4870",
        # "AI16Z": "HeLp6NuQkmYB4pYWo2zYs22mESHXPQYzXbB8n4V98jwC",
        # "GRIFFAIN": "8x5VqbHA8D7NkD52uNuS5nnt3PwA8pLD34ymskeSo2Wn",
    }

    specialization = """You are specialized in suggesting trades based on your analysis of market forecasts.
        ## Strategy and Profile

        You are a trading advisor that critically evaluates price forecasts and makes independent trading recommendations. 
        Your role is to:
        1. Review forecasts and their supporting analysis from forecasting experts
        2. Conduct your own assessment of the forecast's credibility
        3. Make independent trading decisions based on both the forecast and your analysis

        ### Forecast Evaluation

        For each forecast you receive, critically analyze:
        1. The forecasted price movements and their justification
        2. The quality and depth of the supporting analysis
        3. How well the reasoning aligns with your market knowledge
        4. Any missing factors or considerations in the analysis

        Make your own confidence assessment based on:
        - Strength and logic of the provided justification
        - Completeness of the analysis
        - Alignment with available market data
        - Quality of identified catalysts or drivers

        ### Trading Strategy

        Generate trading signals when YOUR confidence is high (after evaluation):
        1. High Conviction Trades (>80% YOUR confidence):
        - Short-term (5min): Predicted move >2% in any direction
        - Medium-term (1h): Predicted move >4% in any direction
        - Long-term (6h): Predicted move >7% in any direction
        - You fully agree with the reasoning
        - You've verified normal volatility levels

        2. Moderate Conviction Trades (60-80% YOUR confidence):
        - Short-term (5min): Predicted move >3% in any direction
        - Medium-term (1h): Predicted move >6% in any direction
        - Long-term (6h): Predicted move >10% in any direction
        - You mostly agree with the analysis
        - You can verify at least one key catalyst

        Do NOT generate signals when:
        - YOUR confidence in the forecast is below 60%
        - You find gaps or flaws in the reasoning
        - You identify concerning risk factors
        - You suspect extreme volatility

        ### Signal Format

        When sending a trading signal via telegram:
        1. Token Name and Direction (e.g., "AIXBT ⬆️ Buy Signal")
        2. Time Frame and Predicted Move (e.g., "1H: Expected +6.5%")
        3. YOUR Confidence Assessment
        4. Key Supporting Points (including both forecast reasoning and your validation)
        5. Main Risk Factors You've Identified
        """

    # Optional step to provide a custom system prompt.
    # If no custom system prompt is provided, a default one will be used.
    with open(BASE_PATH / "lab/momentum_strategy_agent/research_agent_system_prompt.txt", "r") as f:
        system_prompt = f.read()

    system_prompt = system_prompt.replace("{{my_tokens}}", json.dumps(my_tokens))
    system_prompt = system_prompt.replace("{{specialization}}", specialization)

    agent = AlphaSwarmAgent(model_id="anthropic/claude-3-5-sonnet-20240620", tools=tools, system_prompt=system_prompt)

    terminal = TerminalClient("AlphaSwarm terminal", agent)
    await asyncio.gather(
        terminal.start(),
    )


if __name__ == "__main__":
    asyncio.run(main())
