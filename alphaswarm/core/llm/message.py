from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Literal, Optional, Sequence


@dataclass
class CacheControl:
    type: Literal["ephemeral"]

    @classmethod
    def ephemeral(cls) -> CacheControl:
        return cls(type="ephemeral")


@dataclass
class ContentBlock:
    type: Literal["text"]
    text: str
    cache_control: Optional[CacheControl] = field(default=None, repr=False)

    @classmethod
    def default(cls, text: str):
        return cls(type="text", text=text)

    @classmethod
    def with_cache(cls, text: str) -> ContentBlock:
        return cls(type="text", text=text, cache_control=CacheControl.ephemeral())


@dataclass
class Message:
    role: Literal["system", "user", "assistant"]
    content: Sequence[ContentBlock]

    @classmethod
    def message(cls, role: Literal["system", "user", "assistant"], content: str, cache: bool = False) -> Message:
        if not cache:
            return cls(role=role, content=[ContentBlock(type="text", text=content)])
        return cls(role=role, content=[ContentBlock.with_cache(content)])

    @classmethod
    def system(cls, message: str, cache: bool = False) -> Message:
        return cls.message(role="system", content=message, cache=cache)

    @classmethod
    def user(cls, message: str, cache: bool = False) -> Message:
        return cls.message(role="user", content=message, cache=cache)

    @classmethod
    def assistant(cls, message: str, cache: bool = False) -> Message:
        return cls.message(role="assistant", content=message, cache=cache)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self, dict_factory=lambda x: {k: v for k, v in x if v is not None})
