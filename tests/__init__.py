import os
from typing import Final
from enum import Enum

DATA_PATH: Final[str] = os.path.join(os.path.dirname(__file__), "data")


class PromptPath(str, Enum):
    basic = os.path.join(DATA_PATH, "prompts", "prompt.yaml")
    structured = os.path.join(DATA_PATH, "prompts", "structured_prompt.yaml")


def get_data_filename(filename: str) -> str:
    return os.path.join(DATA_PATH, filename)
