from __future__ import annotations

from typing import Any, Dict, Literal, Optional, Union

import yaml
from pydantic import BaseModel

from .base import PromptPairBase, PromptTemplateBase, StrippedStr
from .structured import StructuredPromptPair


class PromptTemplate(PromptTemplateBase):
    template: StrippedStr

    def get_template(self) -> str:
        return self.template


class PromptPair(PromptPairBase):
    system: PromptTemplate
    user: Optional[PromptTemplate] = None


class LLMConfig(BaseModel):
    model: str
    params: Optional[Dict[str, Any]] = None


class PromptConfig(BaseModel):
    """
    Prompt configuration object.
    Contains prompt pair, optional metadata, and optional LLM configuration.
    If LLM configuration is specified, it could be used to generate an LLMFunction.
    """

    kind: Literal["Prompt", "StructuredPrompt"]
    prompt: Union[PromptPair, StructuredPromptPair]
    metadata: Optional[Dict[str, Any]] = None
    llm: Optional[LLMConfig] = None

    @property
    def has_llm_config(self) -> bool:
        return self.llm is not None

    @classmethod
    def from_yaml(cls, path: str) -> PromptConfig:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)
