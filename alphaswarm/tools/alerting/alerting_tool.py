from alphaswarm.tools.strategy_analysis.generic.generic_analysis import StrategyAnalysis
from smolagents import Tool


class SendTradeAlert(Tool):
    name = "SendTradeAlert"
    description = """Send a trade alert to the user."""
    inputs = {
        "analysis": {
            "type": "object",
            "required": True,
            "description": "A StrategyAnalysis object that contains a non-empty list of alerts.",
        },
    }
    output_type = "object"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def forward(self, analysis: StrategyAnalysis) -> None:
        if not isinstance(analysis, StrategyAnalysis):
            raise ValueError("Parameter `analysis` must be a StrategyAnalysis object, got {type(analysis)} instead.")
        if len(analysis.alerts) == 0:
            raise ValueError("No alerts found in the analysis.")
        print(f"***Simulating sending trade alert for {len(analysis.alerts)} alerts.***")
        print(analysis)
