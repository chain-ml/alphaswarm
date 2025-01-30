import os
from typing import Any, Dict

import yaml
from alphaswarm.config import CONFIG_PATH


def load_strategy_config() -> Dict[str, Any]:
    strategy_path = os.path.join(CONFIG_PATH, "strategy_config.yaml")
    try:
        with open(strategy_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise Exception("No trading strategy exists. Please configure a strategy.")
