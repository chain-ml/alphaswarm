from pathlib import Path
from typing import Union

from alphaswarm.config import CONFIG_PATH


def read_text_file_to_string(file_path: Union[str, Path]) -> str:
    "Attempts to read a text file and return its contents as a string."
    try:
        path = Path(file_path) if isinstance(file_path, str) else file_path
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise FileNotFoundError(f"File not found: {file_path}") from e
    except Exception as e:
        raise Exception(f"Error while reading file: {str(e)}") from e


def load_strategy_config() -> str:
    """Loads the trading strategy configuration from the config directory."""
    strategy_path = CONFIG_PATH / "momentum_strategy_config.md"
    try:
        return read_text_file_to_string(strategy_path)
    except FileNotFoundError:
        raise Exception("No trading strategy exists. Please configure a strategy.")
