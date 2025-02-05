from datetime import datetime
from decimal import Decimal

import dotenv
import matplotlib.pyplot as plt
from alphaswarm.services.alchemy import HistoricalPrice, HistoricalPriceBySymbol
from lab.forecasting_agent.price_forecasting_tool import PriceForecast, PriceForecastResponse
from smolagents import Tool


class CreateImageTool(Tool):
    name = "create_forecasting_image"
    description = """Creates an image of the forecasting agent's output.
    Outputs the path to the image (for example, to use in a Telegram message).
    Make sure that the historical data and forecast timeframes are aligned!
    """
    inputs = {
        "historical_data": {
            "type": "object",
            "description": "The HistoricalPriceBySymbol object to create an image from (output of AlchemyPriceHistoryBySymbol).",
        },
        "forecast": {
            "type": "object",
            "description": "The PriceForecastResponse object to create an image from (output of PriceForecastingTool).",
        },
    }
    output_type = "string"

    def __init__(self):
        super().__init__()

    def parse_datetime(self, dt_str):
        """Flexible datetime parsing that handles both datetime objects and strings."""
        if isinstance(dt_str, datetime):
            return dt_str
        try:
            # Try different datetime formats
            for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"]:
                try:
                    return datetime.strptime(dt_str, fmt)
                except ValueError:
                    continue
            raise ValueError(f"Unable to parse datetime: {dt_str}")
        except Exception as e:
            raise ValueError(f"DateTime parsing error: {e}")

    def forward(self, historical_data: HistoricalPriceBySymbol, forecast: PriceForecastResponse) -> str:
        # Create figure and axis
        fig, ax = plt.subplots(figsize=(12, 6))

        # Process and plot historical data point by point
        historical_dates = []
        historical_prices = []
        for point in historical_data.data:
            try:
                date = self.parse_datetime(point.timestamp)
                historical_dates.append(date)
                historical_prices.append(float(point.value))
            except (ValueError, TypeError) as e:
                print(f"Warning: Skipping invalid historical data point: {e}")
                continue

        if historical_dates and historical_prices:
            ax.plot(historical_dates, historical_prices, "b-", label="Historical")

        # Process and plot forecast data point by point
        forecast_dates = []
        forecast_prices = []
        forecast_lower = []
        forecast_upper = []

        for point in forecast.forecast:
            try:
                date = self.parse_datetime(point.timestamp)
                forecast_dates.append(date)
                forecast_prices.append(float(point.price))
                forecast_lower.append(float(point.lower_confidence_bound))
                forecast_upper.append(float(point.upper_confidence_bound))
            except (ValueError, TypeError) as e:
                print(f"Warning: Skipping invalid forecast point: {e}")
                continue

        if forecast_dates and forecast_prices:
            ax.plot(forecast_dates, forecast_prices, "r--", label="Forecast")
            ax.fill_between(
                forecast_dates, forecast_lower, forecast_upper, color="r", alpha=0.2, label="Confidence Interval"
            )

        # Customize plot
        ax.set_title(f"Price Forecast for {historical_data.symbol}")
        ax.set_xlabel("Date")
        ax.set_ylabel("Price")
        ax.grid(True)
        ax.legend()

        # Format dates on x-axis
        plt.gcf().autofmt_xdate()  # Better date formatting

        # Save plot
        path = f"forecast_{historical_data.symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(path, bbox_inches="tight")  # Added bbox_inches='tight' for better layout
        plt.close()

        return path


if __name__ == "__main__":
    dotenv.load_dotenv()
    tool = CreateImageTool()

    # Test data
    historical_data = HistoricalPriceBySymbol(
        symbol="ETH",
        data=[
            HistoricalPrice(value=Decimal("3114.4358854363"), timestamp=datetime(2025, 1, 30)),
            HistoricalPrice(value=Decimal("3248.2494843523"), timestamp=datetime(2025, 1, 31)),
            HistoricalPrice(value=Decimal("3296.3906348437"), timestamp=datetime(2025, 2, 1)),
            HistoricalPrice(value=Decimal("3125.0386801321"), timestamp=datetime(2025, 2, 2)),
            HistoricalPrice(value=Decimal("2862.6976188716"), timestamp=datetime(2025, 2, 3)),
            HistoricalPrice(value=Decimal("2877.8138239499"), timestamp=datetime(2025, 2, 4)),
            HistoricalPrice(value=Decimal("2740.380976276"), timestamp=datetime(2025, 2, 5)),
        ],
    )

    forecast = PriceForecastResponse(
        reason="I reasoned hard and there's my forecast",
        forecast=[
            PriceForecast(
                timestamp=datetime(2025, 2, 6), price=2900, lower_confidence_bound=2000, upper_confidence_bound=4000
            ),
            PriceForecast(
                timestamp=datetime(2025, 2, 7), price=3000, lower_confidence_bound=2500, upper_confidence_bound=5000
            ),
        ],
    )

    print(tool.forward(historical_data=historical_data, forecast=forecast))
