from __future__ import annotations

from typing import Any, Dict, Optional, Union

import yaml
from pydantic import BaseModel, field_validator

from .base import PromptPairBase, PromptTemplateBase
from .structured import StructuredPromptPair


class PromptTemplate(PromptTemplateBase):
    template: str

    @field_validator("template")
    @classmethod
    def strip_template(cls, template: str) -> str:
        # TODO: use StringConstraints in these cases
        return template.strip()

    def get_template(self) -> str:
        return self.template


class PromptPair(PromptPairBase):
    system: PromptTemplate
    user: Optional[PromptTemplate] = None


class LLMConfig(BaseModel):
    model: str
    params: Dict[str, Any] = {}


class PromptConfig(BaseModel):
    prompt: Union[PromptPair, StructuredPromptPair]
    metadata: Optional[Dict[str, Any]] = None
    llm: Optional[LLMConfig] = None

    @classmethod
    def from_yaml(cls, path: str) -> PromptConfig:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)
