from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from alphaswarm.services.alchemy import AlchemyClient
from alphaswarm.tools.forecasting.price_forecasting_tool import PriceForecastingTool


@pytest.fixture
def price_forecasting_tool() -> PriceForecastingTool:
    return PriceForecastingTool()


def test_price_forecasting_tool(price_forecasting_tool: PriceForecastingTool, alchemy_client: AlchemyClient) -> None:
    # Get historical price data for USDC
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=7)  # Get a week of historical data
    historical_data = alchemy_client.get_historical_prices_by_symbol(
        symbol="USDC", start_time=start, end_time=end, interval="1h"
    )

    # Call the forecasting tool
    forecast_horizon = "24 hours"
    supporting_context = ["USDC has maintained strong stability near $1 [Source: Market Data, Timeframe: last 7 days]"]

    result = price_forecasting_tool.forward(
        historical_price_data=historical_data, forecast_horizon=forecast_horizon, supporting_context=supporting_context
    )

    # Verify response structure and basic expectations
    assert result is not None
    assert result.reasoning is not None
    assert len(result.reasoning) > 0
    assert len(result.forecast) > 0

    # Verify forecast data
    for forecast in result.forecast:
        assert isinstance(forecast.timestamp, datetime)
        assert isinstance(forecast.price, Decimal)
        assert isinstance(forecast.lower_confidence_bound, Decimal)
        assert isinstance(forecast.upper_confidence_bound, Decimal)
        assert forecast.lower_confidence_bound <= forecast.price <= forecast.upper_confidence_bound
        # Since we're forecasting USDC which is a stablecoin, expect values close to 1
        assert Decimal("0.9") <= forecast.price <= Decimal("1.1")
