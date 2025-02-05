from smolagents import Tool


class CallForecastingAgentTool(Tool):
    name = "CallForecastingAgentTool"
    description = """Call the forecasting agent to get a detailed price forecast for a token. 
    The forecast will return predicted prices at the specified frequency intervals over the requested time horizon."""
    inputs = {
        "token_address_or_symbol": {
            "type": "string",
            "description": "The token address or symbol to analyze (e.g. 'ETH', '0x...').",
        },
        "network": {
            "type": "string",
            "description": "The blockchain network where the token exists (e.g. 'eth-mainnet', 'base-mainnet').",
            "default": "eth-mainnet",
            "nullable": False,
        },
        "forecast_horizon": {
            "type": "string",
            "description": "How far into the future to forecast (e.g. '1h', '4h', '1d', '1w'). Use format: number + unit (m=minutes, h=hours, d=days, w=weeks).",
            "default": "1h",
            "nullable": False,
        },
        "forecast_frequency": {
            "type": "string",
            "description": "The time interval between each forecast point (e.g. '5m', '15m', '1h'). Must be smaller than forecast_horizon. Use format: number + unit (m=minutes, h=hours).",
            "default": "5m",
            "nullable": False,
        },
    }
    output_type = "string"

    def __init__(self):
        super().__init__()

        # Initialize the forecasting agent

    def forward(
        self,
        token_address_or_symbol: str,
        network: str = "eth-mainnet",
        forecast_horizon: str = "1h",
        forecast_frequency: str = "5m",
    ) -> str:
        return f"""
        The following is a *mock forecast* for the token {token_address_or_symbol} on the {network} network.
        
        ```csv
        timestamp, price, confidence_lower, confidence_upper
        2025-01-01 00:00:00, 100.00, 90.00, 110.00
        2025-01-01 00:05:00, 101.00, 91.00, 111.00
        2025-01-01 00:10:00, 102.00, 92.00, 112.00
        2025-01-01 00:15:00, 103.00, 93.00, 113.00
        2025-01-01 00:20:00, 104.00, 94.00, 114.00
        2025-01-01 00:25:00, 105.00, 95.00, 115.00
        ```

        ```justification
        The forecast is based on the token's historical price data and market trends.
        I also incorporated the token's market cap, trading volume, and other relevant metrics to provide a more comprehensive forecast.
        ```
        """
