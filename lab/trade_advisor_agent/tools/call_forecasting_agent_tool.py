import asyncio

from lab.forecasting_agent.forecasting_agent import ForecastingAgent
from smolagents import Tool


class CallForecastingAgentTool(Tool):
    name = "CallForecastingAgentTool"
    description = """Call the forecasting agent to get a detailed price forecast for a token. 
    The forecast will return predicted prices at the specified frequency intervals over the requested time horizon."""
    inputs = {
        "task_for_forecasting_agent": {
            "type": "string",
            "description": """The task for the forecasting agent. Must include the token address or symbol, network, forecast horizon, and forecast frequency.
            For example: "Please give me a forecast for the price of VIRTUAL on the base network for the next 1 hour in 5-minute intervals.""",
        },
    }
    output_type = "string"

    def __init__(self) -> None:
        super().__init__()

        # Initialize the forecasting agent
        self.forecasting_agent = ForecastingAgent()

    def forward(
        self,
        task_for_forecasting_agent: str,
    ) -> str:
        return str(asyncio.run(self.forecasting_agent.process_message(task_for_forecasting_agent)))
