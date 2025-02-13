from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from alphaswarm import BASE_PATH
from alphaswarm.core.base_tool import AlphaSwarmBaseTool
from alphaswarm.core.llm.llm_function import LLMFunctionFromPromptFiles
from pydantic import BaseModel, Field

from ..strategy import Strategy

TOOLS_PATH = Path(BASE_PATH) / "alphaswarm" / "tools"


class AlertItem(BaseModel):
    # Core token identification
    metadata: Dict[str, Any] = Field(
        description="Token metadata including symbol, address, chain, and any other relevant token information",
        default_factory=dict,
    )

    # Alert details
    rule_description: str = Field(description="Description of the rule that was triggered")
    value: float = Field(description="The measured value related to this alert")
    supporting_data: Dict[str, Any] = Field(
        description="Additional context about why this rule was triggered, including relevant metrics or observations",
        default_factory=dict,
    )


class StrategyAnalysis(BaseModel):
    summary: str = Field(description="A concise summary of the overall analysis and key findings")
    alerts: List[AlertItem] = Field(description="List of triggered rules and their details", default_factory=list)


class AnalyzeTradingStrategy(AlphaSwarmBaseTool):
    """
    Analyze the trading strategy against the provided data and decide if any of the strategy rules are triggered.
    Returns a StrategyAnalysis object, which contains a summary of the analysis and a list of triggered rules and their details.
    """

    inputs = {
        "token_data": {
            "type": "string",
            "required": True,
            "description": "A JSON-formatted string containing the token data to analyze, keyed by token symbol.",
        },
    }
    output_type = "object"

    def __init__(self, strategy: Strategy, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.strategy = strategy

        # Init the LLMFunction
        prompts_path = TOOLS_PATH / "strategy_analysis" / "generic" / "prompts"
        self._llm_function = LLMFunctionFromPromptFiles(
            model_id=strategy.model_id,
            response_model=StrategyAnalysis,
            system_prompt_path=str(prompts_path / "system_prompt.md"),
            user_prompt_path=str(prompts_path / "user_prompt.md"),
        )

    def forward(self, token_data: str) -> StrategyAnalysis:
        response = self._llm_function.execute(
            user_prompt_params={
                "token_data": token_data,
                "strategy_rules": self.strategy.rules,
            }
        )
        return response
