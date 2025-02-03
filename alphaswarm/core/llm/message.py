from __future__ import annotations

import base64
import mimetypes
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Literal, Optional, Sequence, Union


@dataclass
class CacheControl:
    type: Literal["ephemeral"]

    @classmethod
    def ephemeral(cls) -> CacheControl:
        return cls(type="ephemeral")


@dataclass
class TextContentBlock:
    type: Literal["text"]
    text: str
    cache_control: Optional[CacheControl] = None

    @classmethod
    def default(cls, text: str):
        return cls(type="text", text=text)

    @classmethod
    def with_cache(cls, text: str) -> ContentBlock:
        return cls(type="text", text=text, cache_control=CacheControl.ephemeral())


@dataclass
class ImageURL:
    url: str

    @classmethod
    def from_path(cls, path: str) -> ImageURL:
        with open(path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")

        mime_type, _ = mimetypes.guess_type(path)
        if mime_type is None:
            mime_type = "image/unknown"

        return cls(url=f"data:{mime_type};base64,{base64_image}")


@dataclass
class ImageContentBlock:
    type: Literal["image_url"]
    image_url: ImageURL


ContentBlock = Union[TextContentBlock, ImageContentBlock]


@dataclass
class Message:
    role: Literal["system", "user", "assistant"]
    content: Sequence[ContentBlock]

    @classmethod
    def create(
        cls,
        role: Literal["system", "user", "assistant"],
        content: str,
        cache: bool = False,
        image_url: Optional[ImageURL] = None,
    ) -> Message:
        """Helper method to create Message from string content and optional ImageURL."""

        content_blocks: List[ContentBlock] = []
        if image_url:
            content_blocks.append(ImageContentBlock(type="image_url", image_url=image_url))
        text_block = TextContentBlock.default(content) if not cache else TextContentBlock.with_cache(content)
        content_blocks.append(text_block)

        return cls(role=role, content=content_blocks)

    @classmethod
    def system(cls, message: str, cache: bool = False) -> Message:
        return cls.create(role="system", content=message, cache=cache)

    @classmethod
    def user(cls, message: str, cache: bool = False) -> Message:
        return cls.create(role="user", content=message, cache=cache)

    @classmethod
    def assistant(cls, message: str, cache: bool = False) -> Message:
        return cls.create(role="assistant", content=message, cache=cache)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self, dict_factory=lambda x: {k: v for k, v in x if v is not None})
