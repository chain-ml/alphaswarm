from __future__ import annotations

import abc
from typing import List, Mapping, Optional, Sequence, Type

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


class PromptFormatterBase(abc.ABC):
    def format(self, sections: Sequence[PromptSection]) -> str:
        return "\n".join(self._format_section(section) for section in sections)

    @abc.abstractmethod
    def _format_section(self, section: PromptSection) -> str:
        pass


class StringPromptFormatter(PromptFormatterBase):
    def __init__(self, section_prefix: str = ""):
        self.section_prefix = section_prefix

    def _format_section(self, section: PromptSection) -> str:
        parts = [f"{self.section_prefix}{section.name}"]
        if section.content:
            parts.append(section.content)
        parts.extend([self._format_section(sec) for sec in section.sections])
        return "\n".join(parts)


class MarkdownPromptFormatter(PromptFormatterBase):
    def _format_section(self, section: PromptSection, indent: int = 1) -> str:
        parts = [f"{'#' * indent} {section.name}", ""]
        if section.content:
            parts.extend([section.content, ""])
        parts.extend([self._format_section(sec, indent + 1) for sec in section.sections])
        return "\n".join(parts)


class XMLPromptFormatter(PromptFormatterBase):
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


FORMATTER_REGISTRY: Mapping[str, Type[PromptFormatterBase]] = {
    "string": StringPromptFormatter,
    "markdown": MarkdownPromptFormatter,
    "xml": XMLPromptFormatter,
}


class StructuredPromptTemplate(PromptTemplateBase):
    sections: List[PromptSection]
    _formatter: PromptFormatterBase

    def set_formatter(self, formatter: PromptFormatterBase) -> None:
        self._formatter = formatter

    def get_template(self) -> str:
        return self._formatter.format(self.sections)


class StructuredPromptPair(BaseModel):
    system: StructuredPromptTemplate
    user: Optional[StructuredPromptTemplate] = None
    formatter: str = "string"
    _formatter: PromptFormatterBase

    @model_validator(mode="after")
    def formatter_validator(self) -> StructuredPromptPair:
        formatter: PromptFormatterBase = self.formatter_string_to_obj(self.formatter)
        self.set_formatter(formatter)
        return self

    @staticmethod
    def formatter_string_to_obj(formatter: str) -> PromptFormatterBase:
        formatter = formatter.lower()
        if formatter not in FORMATTER_REGISTRY:
            raise ValueError(
                f"Unknown formatter: `{formatter}`. Available formatters: {', '.join(FORMATTER_REGISTRY.keys())}"
            )

        formatter_cls = FORMATTER_REGISTRY[formatter]
        return formatter_cls()

    def set_formatter(self, formatter: PromptFormatterBase) -> None:
        self._formatter = formatter
        self.system.set_formatter(self._formatter)
        if self.user:
            self.user.set_formatter(self._formatter)
