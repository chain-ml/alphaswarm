import os
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
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


class PriceForecastLLMResponse(BaseModel):
    reason: str = Field(description="The reasoning behind the forecast")
    forecast: List[PriceForecast] = Field(description="The forecasted prices of the token")


class PriceForecastResponse(BaseModel):
    reason: str
    historical_price_data: HistoricalPriceBySymbol
    forecast: List[PriceForecast]
    image_path: str


class PriceForecastingTool(Tool):
    name = "PriceForecastingTool"
    description = """Forecast the price of a token based on historical price data and other relevant market context.
    
    Returns a `PriceForecastResponse` object.

    The `PriceForecastResponse` object has the following fields:
    - reason: The reasoning behind the forecast
    - historical_price_data: HistoricalPriceBySymbol object passed as input to the tool
    - forecast: A list of `PriceForecast` objects, each containing a timestamp, a forecasted price, a lower confidence bound, and an upper confidence bound
    - image_path: The path to the image to send to the Telegram

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
        "market_context": {
            "type": "string",
            "description": "Relevant market context for the token. For every piece of information, include source and timeframe. If those are not available, state that or do not include them.",
            "nullable": True,
        },
    }
    output_type = "object"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Init the LLMFunction
        self._llm_function = LLMFunctionFromPromptFiles(
            model_id="anthropic/claude-3-5-sonnet-20241022",
            response_model=PriceForecastLLMResponse,
            system_prompt_path=os.path.join(BASE_PATH, "lab", "forecasting_agent", "prompts", "system_prompt.md"),
            user_prompt_path=os.path.join(BASE_PATH, "lab", "forecasting_agent", "prompts", "user_prompt.md"),
        )

    def forward(
        self,
        historical_price_data: HistoricalPriceBySymbol,
        forecast_horizon: str,
        market_context: Optional[str] = None,
    ) -> PriceForecastResponse:
        response: PriceForecastLLMResponse = self._llm_function.execute(
            user_prompt_params={
                "market_context": market_context if market_context is not None else "No additional context provided",
                "historical_price_data": str(historical_price_data),
                "forecast_horizon": forecast_horizon,
            }
        )

        final_response = PriceForecastResponse(
            reason=response.reason,
            historical_price_data=historical_price_data,
            forecast=response.forecast,
            image_path=self._create_image(historical_price_data, response.forecast),
        )
        return final_response

    @staticmethod
    def _create_image(historical_price_data: HistoricalPriceBySymbol, forecast: List[PriceForecast]) -> str:
        fig, ax = plt.subplots(figsize=(12, 6))

        historical_dates = mdates.date2num([p.timestamp for p in historical_price_data.data])
        historical_prices = [float(p.value) for p in historical_price_data.data]
        ax.plot(historical_dates, historical_prices, "b-", label="Historical")

        forecast_dates = mdates.date2num([p.timestamp for p in forecast])
        forecast_prices = [float(p.price) for p in forecast]
        forecast_lower = [float(p.lower_confidence_bound) for p in forecast]
        forecast_upper = [float(p.upper_confidence_bound) for p in forecast]

        ax.plot(forecast_dates, forecast_prices, "r--", label="Forecast")
        ax.fill_between(
            forecast_dates, forecast_lower, forecast_upper, color="r", alpha=0.2, label="Confidence Interval"
        )

        ax.set_title(f"Price Forecast for {historical_price_data.symbol}")
        ax.set_xlabel("Date")
        ax.set_ylabel("Price")
        ax.grid(True)
        ax.legend()

        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
        plt.gcf().autofmt_xdate()

        path = f"forecast_{historical_price_data.symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(path, bbox_inches="tight")
        plt.close()

        return path
