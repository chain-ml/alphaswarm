import os
from decimal import Decimal
from typing import List, Optional

from alphaswarm.config import BASE_PATH
from alphaswarm.core.llm.llm_function import LLMFunctionFromPromptFiles
from pydantic import BaseModel, Field
from smolagents import Tool


class PriceForecast(BaseModel):
    timestamp: str = Field(description="The timestamp of the forecast")
    price: Decimal = Field(description="The forecasted median price of the token")
    lower_confidence_bound: Decimal = Field(description="The lower confidence bound of the forecast")
    upper_confidence_bound: Decimal = Field(description="The upper confidence bound of the forecast")


class PriceForecastResponse(BaseModel):
    reason: str = Field(description="The reasoning behind the forecast")
    forecast: List[PriceForecast] = Field(description="The forecasted prices of the token")


class PriceForecastingTool(Tool):
    name = "PriceForecastingTool"
    description = """Forecast the price of a token based on historical price data and other relevant market context.
    
    Returns a `PriceForecastResponse` object.

    The `PriceForecastResponse` object has the following fields:
    - reason: The reasoning behind the forecast
    - forecast: A list of `PriceForecast` objects, each containing a timestamp and a price

    A `PriceForecast` object has the following fields:
    - timestamp: The timestamp of the forecast
    - price: The forecasted median price of the token
    - lower_confidence_bound: The lower confidence bound of the forecast
    - upper_confidence_bound: The upper confidence bound of the forecast
    """
    inputs = {
        "historical_price_data": {
            "type": "string",
            "description": "Historical price data for the token",
        },
        "forecast_horizon": {
            "type": "string",
            "description": "Instructions for the forecast horizon",
        },
        "market_context": {
            "type": "string",
            "description": "Relevant market context for the token",
            "nullable": True,
        },
    }
    output_type = "object"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Init the LLMFunction
        self._llm_function = LLMFunctionFromPromptFiles(
            model_id="anthropic/claude-3-5-sonnet-20241022",
            response_model=PriceForecastResponse,
            system_prompt_path=os.path.join(BASE_PATH, "lab", "forecasting_agent", "prompts", "system_prompt.md"),
            user_prompt_path=os.path.join(BASE_PATH, "lab", "forecasting_agent", "prompts", "user_prompt.md"),
        )

    def forward(
        self, historical_price_data: str, forecast_horizon: str, market_context: Optional[str] = None
    ) -> PriceForecastResponse:
        response = self._llm_function.execute(
            user_prompt_params={
                "market_context": market_context if market_context is not None else "No additional context provided",
                "historical_price_data": historical_price_data,
                "forecast_horizon": forecast_horizon,
            }
        )
        return response
