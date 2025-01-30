from alphaswarm.tools.strategies.momentum.momentum_analysis_tool import StrategyAnalysis
from smolagents import Tool


class SendTradeAlert(Tool):
    name = "SendTradeAlert"
    description = """Send a trade alert to the user."""
    inputs = {
        "analysis": {
            "type": "object",
            "required": True,
            "description": "A StrategyAnalysis object that contains a non-empty list of MomentumItems.",
        },
    }
    output_type = "object"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def forward(self, analysis: StrategyAnalysis) -> None:
        if not isinstance(analysis, StrategyAnalysis):  # type: ignore[unreachable]
            raise ValueError("Parameter `analysis` must be a StrategyAnalysis object, got {type(analysis)} instead.")
        if len(analysis.momentum_items) == 0:
            raise ValueError("No momentum items found in the analysis.")
        print(f"***Simulating sending trade alert for {len(analysis.momentum_items)} momentum items.***")
        print(analysis)
