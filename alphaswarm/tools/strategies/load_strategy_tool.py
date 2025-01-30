from typing import Any, Dict

from alphaswarm.utils import load_strategy_config
from smolagents import Tool

class LoadStrategyTool(Tool):
    name = "LoadStrategyTool"
    description = """Loads and returns the current strategy configuration"""
    inputs: Dict = {}
    output_type = "object"

    def forward(self) -> Dict[str, Any]:
        return load_strategy_config()