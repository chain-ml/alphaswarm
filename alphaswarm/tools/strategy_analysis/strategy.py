from __future__ import annotations

from alphaswarm.utils import load_strategy_config


class Strategy:

    def __init__(self, *, rules: str, model_id: str = "anthropic/claude-3-5-sonnet-20241022") -> None:
        self.rules = rules
        self.model_id = model_id

    @classmethod
    def from_file(cls, *, filename: str, model_id: str = "anthropic/claude-3-5-sonnet-20241022") -> Strategy:
        strategy_config = load_strategy_config(filename=filename)
        # model_id should come from the config
        return cls(rules=strategy_config, model_id=model_id)
