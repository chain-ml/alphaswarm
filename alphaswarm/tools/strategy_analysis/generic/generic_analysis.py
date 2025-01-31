import os
from typing import Any, Dict, List

import yaml
from alphaswarm.config import BASE_PATH, CONFIG_PATH
from alphaswarm.utils import LLMFunctionFromPromptFiles, load_strategy_config
from pydantic import BaseModel, Field
from smolagents import Tool


class AlertItem(BaseModel):
    # Core token identification
    metadata: Dict[str, Any] = Field(
        description="Token metadata including symbol, address, chain, and any other relevant token information",
        default_factory=dict
    )
    
    # Alert details
    rule_description: str = Field(description="Description of the rule that was triggered")
    value: float = Field(description="The measured value related to this alert")
    supporting_data: Dict[str, Any] = Field(
        description="Additional context about why this rule was triggered, including relevant metrics or observations",
        default_factory=dict
    )


class StrategyAnalysis(BaseModel):
    summary: str = Field(
        description="A concise summary of the overall analysis and key findings"
    )
    alerts: List[AlertItem] = Field(
        description="List of triggered rules and their details",
        default_factory=list
    )


class GenericStrategyAnalysisTool(Tool):
    name = "GenericStrategyAnalysisTool"
    description = """Analyze the trading strategy against the provided data and decide if any of the strategy rules are triggered. 
    Returns a StrategyAnalysis object, which contains a summary of the analysis and a list of triggered rules and their details.
    This tool will apply the same strategy config that is found under the "## Strategy Config" section of the User Context.
    """
    inputs = {
        "token_data": {
            "type": "string",
            "required": True,
            "description": "A JSON-formatted string containing the token data to analyze, keyed by token symbol.",
        },
    }
    output_type = "object"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.strategy_config = load_strategy_config()

        # Init the LLMFunction
        self._llm_function = LLMFunctionFromPromptFiles(
            model_id="anthropic/claude-3-5-sonnet-latest",  # this should come from the config
            response_model=StrategyAnalysis,
            system_prompt_path=os.path.join(
                BASE_PATH, "alphaswarm", "tools", "strategy_analysis", "generic", "prompts", "system_prompt.md"
            ),
            user_prompt_path=os.path.join(
                BASE_PATH, "alphaswarm", "tools", "strategy_analysis", "generic", "prompts", "user_prompt.md"
            ),
        )

    def forward(self, token_data: str) -> StrategyAnalysis:
        response = self._llm_function.execute(
            user_prompt_params={
                "token_data": token_data,
                "strategy_rules": self.strategy_config,
            }
        )
        return response
