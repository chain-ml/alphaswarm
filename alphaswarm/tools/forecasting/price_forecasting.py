import os
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from alphaswarm.config import BASE_PATH
from alphaswarm.core.llm import LLMFunctionTemplated
from alphaswarm.core.tool import AlphaSwarmToolBase
from alphaswarm.services.alchemy import HistoricalPriceBySymbol
from pydantic import BaseModel, Field


class PriceForecast(BaseModel):
    timestamp: datetime = Field(description="The timestamp of the forecast")
    price: Decimal = Field(description="The forecasted median price of the token")
    lower_confidence_bound: Decimal = Field(description="The lower confidence bound of the forecast")
    upper_confidence_bound: Decimal = Field(description="The upper confidence bound of the forecast")


class PriceForecastResponse(BaseModel):
    reasoning: str = Field(description="The reasoning behind the forecast")
    forecast: List[PriceForecast] = Field(description="The forecasted prices of the token")


class ForecastTokenPrice(AlphaSwarmToolBase):
    """
    Forecast the price of a token based on historical price data and supporting context retrieved using other tools.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        # Init the LLMFunction
        self._llm_function = LLMFunctionTemplated.from_files(
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
        """
        Args:
            historical_price_data: Historical price data for the token; output of AlchemyPriceHistoryBySymbol tool
            forecast_horizon: Instructions for the forecast horizon
            supporting_context: An optional list of strings, each representing an element of context to support the forecast. Each element should include a source and a timeframe, e.g.: '...details... [Source: Web Search, Timeframe: last 2 days]'
        """
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
