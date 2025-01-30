import logging
import os
from pydantic import BaseModel, Field
from typing import Any, Dict, List
import yaml

from smolagents import Tool

from alphaswarm.config import BASE_PATH, CONFIG_PATH
from alphaswarm.utils import LLMFunctionFromPromptFiles

class MomentumItem(BaseModel):
    symbol: str = Field(description="The symbol of the token.")
    rule: str = Field(description="The rule that was satisfied.")
    value: float = Field(description="The value of the rule that was satisfied.")

class StrategyAnalysis(BaseModel):
    analysis: str = Field(description="A summary of the analysis.")
    momentum_items: List[MomentumItem] = Field(description="A list of metric rules that were satisfied.")

class PriceMomentumStrategyAnalysisTool(Tool):
    name = "PriceMomentumStrategyAnalysisTool"
    description = """Analyze the price momentum strategy against the percentage price changes of relevant tokens over the last 24 hours
    and decide if the strategy rules are triggered. Returns a StrategyAnalysis object.
    """
    inputs = {
        "percent_price_change_24_hour": {
            "type": "string",
            "required": True,
            "description": "The percentage price changes for a list of tokens over the last 24 hours.",
        },
    }
    output_type = "object"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.strategy_config = self._load_strategy_config()

        # Init the LLMFunction
        self._llm_function = LLMFunctionFromPromptFiles(
            model_id="anthropic/claude-3-5-sonnet-latest",  # this should come from the config
            response_model=StrategyAnalysis,
            system_prompt_path=os.path.join(BASE_PATH, "alphaswarm", "tools", "strategies", "momentum", "prompts", "momentum_system_prompt.md"),
            system_prompt_params={},
            user_prompt_path=os.path.join(BASE_PATH, "alphaswarm", "tools", "strategies", "momentum", "prompts", "momentum_user_prompt.md"),
        )

    
    def forward(self, percent_price_change_24_hour: str) -> StrategyAnalysis:
        response = self._llm_function.execute(
            user_prompt_params={
                "price_changes": percent_price_change_24_hour,
                "momentum_strategy_rules": self.strategy_config,
            }
        )
        return response


    def _load_strategy_config(self) -> Dict[str, Any]:
        strategy_path = os.path.join(CONFIG_PATH, "reference_strategy_config.yaml")
        try:
            with open(strategy_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise Exception("No trading strategy exists. Please configure a strategy.")

