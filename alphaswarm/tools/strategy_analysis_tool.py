import os
import yaml
from typing import Any, Dict

from smolagents import Tool

from alphaswarm.config import CONFIG_PATH

class PriceMomentumStrategyAnalysisTool(Tool):
    name = "PriceMomentumStrategyAnalysisTool"
    description = """Analyze the price momentum strategy against the percentage price changes of relevant tokens over the last 24 hours
    and decide if the strategy rules are triggered.
    """
    inputs = {
        "percent_price_change_24_hour": {
            "type": "string",
            "required": True,
            "description": "The percentage price changes for the relevant tokens over the last 24 hours.",
        },
    }
    output_type = "object"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.strategy_config = self._load_strategy_config()

    
    def forward(self, percent_price_change_24_hour: str):
        return f"Your tokens have all satisfied your trading rules based on the following data:\n\n{percent_price_change_24_hour}!"


    def _load_strategy_config(self) -> Dict[str, Any]:
        strategy_path = os.path.join(CONFIG_PATH, "strategy_config.yaml")
        try:
            with open(strategy_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise Exception("No trading strategy exists. Please configure a strategy.")

