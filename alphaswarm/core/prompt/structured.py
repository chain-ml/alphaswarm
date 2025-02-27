from __future__ import annotations

import abc
from typing import Optional, List, Sequence, Mapping, Type, Union

from pydantic import BaseModel, field_validator, model_validator

from .base import PromptTemplateBase


class PromptSection(BaseModel):
    name: str
    content: Optional[str] = None
    sections: List[PromptSection] = []

    @field_validator("content")
    @classmethod
    def strip_content(cls, content: Optional[str]) -> Optional[str]:
        if isinstance(content, str):
            return content.strip()
        return content


class PromptFormatter(abc.ABC):
    def format(self, sections: Sequence[PromptSection]) -> str:
        return "\n".join(self._format_section(section) for section in sections)

    @abc.abstractmethod
    def _format_section(self, section: PromptSection) -> str:
        pass


class StringPromptFormatter(PromptFormatter):
    def __init__(self, section_prefix: str = ""):
        self.section_prefix = section_prefix

    def _format_section(self, section: PromptSection) -> str:
        parts = [f"{self.section_prefix}{section.name}"]
        if section.content:
            parts.append(section.content)
        parts.extend([self._format_section(sec) for sec in section.sections])
        return "\n".join(parts)


class MarkdownPromptFormatter(PromptFormatter):
    def _format_section(self, section: PromptSection, indent: int = 1) -> str:
        parts = [f"{'#' * indent} {section.name}", ""]
        if section.content:
            parts.extend([section.content, ""])
        parts.extend([self._format_section(sec, indent + 1) for sec in section.sections])
        return "\n".join(parts)


class XMLPromptFormatter(PromptFormatter):
    INDENT_DIFF: str = "  "

    def _format_section(self, section: PromptSection, indent: str = "") -> str:
        name_snake_case = section.name.lower().replace(" ", "_")
        parts = [f"{indent}<{name_snake_case}>"]

        if section.content:
            content_lines = section.content.split("\n")
            content = "\n".join([f"{indent}{self.INDENT_DIFF}{line}" for line in content_lines])
            parts.append(content)

        parts.extend([self._format_section(sec, indent + self.INDENT_DIFF) for sec in section.sections])
        parts.append(f"{indent}</{name_snake_case}>")
        return "\n".join(parts)


FORMATTER_REGISTRY: Mapping[str, Type[PromptFormatter]] = {
    "string": StringPromptFormatter,
    "markdown": MarkdownPromptFormatter,
    "xml": XMLPromptFormatter,
}


class StructuredPromptTemplate(PromptTemplateBase):
    sections: List[PromptSection]

    def get_template(self) -> str:
        return self._formatter.format(self.sections)


class StructuredPromptPair(BaseModel):
    system: StructuredPromptTemplate
    user: Optional[StructuredPromptTemplate] = None
    formatter: str = "string"

    @staticmethod
    def resolve_formatter(formatter: Union[str, PromptFormatter]) -> PromptFormatter:
        # TODO: save in _formatter
        if isinstance(formatter, PromptFormatter):
            return formatter
        if formatter.lower() in FORMATTER_REGISTRY:
            return FORMATTER_REGISTRY[formatter.lower()]()
        raise ValueError(
            f"Unknown formatter: `{formatter}`. Available formatters: {', '.join(FORMATTER_REGISTRY.keys())}"
        )

    @model_validator(mode="after")
    def set_formatter(self):
        self._formatter = self.resolve_formatter(self.formatter)
        self.system._formatter = self._formatter
        if self.user:
            self.user._formatter = self._formatter

        return self
