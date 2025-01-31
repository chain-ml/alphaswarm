import os
from alphaswarm.config import CONFIG_PATH


def load_strategy_config() -> str:
    strategy_path = os.path.join(CONFIG_PATH, "strategy_config.md")
    try:
        with open(strategy_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise Exception("No trading strategy exists. Please configure a strategy.")
