from pathlib import Path
from typing import Union


def read_text_file_to_string(file_path: Union[str, Path]) -> str:
    "Attempts to read a text file and return its contents as a string."
    try:
        path = Path(file_path) if isinstance(file_path, str) else file_path
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except Exception as e:
        raise Exception(f"Error while reading file: {str(e)}")
