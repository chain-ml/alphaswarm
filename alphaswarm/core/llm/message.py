from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Literal


@dataclass
class Message:
    role: Literal["system", "user", "assistant"]
    content: str

    @classmethod
    def system(cls, message: str) -> Message:
        return cls(role="system", content=message)

    @classmethod
    def user(cls, message: str) -> Message:
        return cls(role="user", content=message)

    @classmethod
    def assistant(cls, message: str) -> Message:
        return cls(role="assistant", content=message)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
