from __future__ import annotations

import abc
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, field_validator


class PromptTemplateBase(BaseModel, abc.ABC):
    @abc.abstractmethod
    def get_template(self) -> str:
        pass


class PromptTemplate(PromptTemplateBase):
    template: str

    @field_validator("template")
    @classmethod
    def strip_template(cls, template: str) -> str:
        return template.strip()

    def get_template(self) -> str:
        return self.template


class PromptPair(BaseModel):
    system: PromptTemplate  # TODO: should be base class
    user: Optional[PromptTemplate] = None


class LLMConfig(BaseModel):
    model: str
    params: Optional[Dict[str, Any]] = None


class PromptConfig(BaseModel):
    kind: str
    prompt: PromptPair
    metadata: Optional[Dict[str, Any]] = None
    llm: Optional[LLMConfig] = None

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, kind: str) -> str:
        if kind not in ["Prompt"]:
            raise ValueError(f"Invalid kind: {kind}")
        return kind

    @classmethod
    def from_yaml(cls, path: str) -> PromptConfig:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)
