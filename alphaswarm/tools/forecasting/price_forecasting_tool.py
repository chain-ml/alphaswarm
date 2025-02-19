import os
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from alphaswarm.config import BASE_PATH
from alphaswarm.core.llm.llm_function import LLMFunctionFromPromptFiles
from alphaswarm.services.alchemy import HistoricalPriceBySymbol
from pydantic import BaseModel, Field
from smolagents import Tool


class PriceForecast(BaseModel):
    timestamp: datetime = Field(description="The timestamp of the forecast")
    price: Decimal = Field(description="The forecasted median price of the token")
    lower_confidence_bound: Decimal = Field(description="The lower confidence bound of the forecast")
    upper_confidence_bound: Decimal = Field(description="The upper confidence bound of the forecast")


class PriceForecastResponse(BaseModel):
    reasoning: str = Field(description="The reasoning behind the forecast")
    forecast: List[PriceForecast] = Field(description="The forecasted prices of the token")


class PriceForecastingTool(Tool):
    name = "PriceForecastingTool"
    description = """Forecast the price of a token based on historical price data and supporting context retrieved using other tools.
    
    Returns a `PriceForecastResponse` object.

    The `PriceForecastResponse` object has the following fields:
    - reasoning: The reasoning behind the forecast
    - historical_price_data: HistoricalPriceBySymbol object passed as input to the tool
    - forecast: A list of `PriceForecast` objects, each containing a timestamp, a forecasted price, a lower confidence bound, and an upper confidence bound

    A `PriceForecast` object has the following fields:
    - timestamp: The timestamp of the forecast
    - price: The forecasted median price of the token
    - lower_confidence_bound: The lower confidence bound of the forecast
    - upper_confidence_bound: The upper confidence bound of the forecast
    """
    inputs = {
        "historical_price_data": {
            "type": "object",
            "description": "Historical price data for the token; output of AlchemyPriceHistoryBySymbol tool",
        },
        "forecast_horizon": {
            "type": "string",
            "description": "Instructions for the forecast horizon",
        },
        "supporting_context": {
            "type": "object",
            "description": """A list of strings, each representing an element of context to support the forecast.
                Each element should include a source and a timeframe, e.g.: '...details... [Source: Web Search, Timeframe: last 2 days]'""",
            "nullable": True,
        },
    }
    output_type = "object"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        # Init the LLMFunction
        self._llm_function = LLMFunctionFromPromptFiles(
            model_id="anthropic/claude-3-5-sonnet-20241022",
            response_model=PriceForecastResponse,
            system_prompt_path=os.path.join(
                BASE_PATH, "alphaswarm", "tools", "forecasting", "prompts", "price_forecasting_system_prompt.md"
            ),
            user_prompt_path=os.path.join(
                BASE_PATH, "alphaswarm", "tools", "forecasting", "prompts", "price_forecasting_user_prompt.md"
            ),
        )

    def forward(
        self,
        historical_price_data: HistoricalPriceBySymbol,
        forecast_horizon: str,
        supporting_context: Optional[List[str]] = None,
    ) -> PriceForecastResponse:
        response: PriceForecastResponse = self._llm_function.execute(
            user_prompt_params={
                "supporting_context": (
                    supporting_context if supporting_context is not None else "No additional context provided"
                ),
                "historical_price_data": str(historical_price_data),
                "forecast_horizon": forecast_horizon,
            }
        )
        return response
