import pytest
from pydantic import ValidationError

from alphaswarm.core.prompt import PromptConfig
from alphaswarm.core.prompt.prompt import (
    PromptTemplate,
    PromptPair,
    LLMConfig,
)
from alphaswarm.core.prompt.structured import (
    PromptSection,
    StructuredPromptTemplate,
    StringPromptFormatter,
    MarkdownPromptFormatter,
    XMLPromptFormatter,
    FORMATTER_REGISTRY,
    StructuredPromptPair,
)
from tests import PromptPath


class TestPromptTemplate:
    def test_get_template(self) -> None:
        template = "Test template with {variable}"
        prompt = PromptTemplate(template=template)
        assert prompt.get_template() == template

    def test_whitespace_stripping(self) -> None:
        template = "  Template with whitespace   "
        prompt = PromptTemplate(template=template)
        assert prompt.template == "Template with whitespace"
        assert prompt.get_template() == "Template with whitespace"


class TestStructuredPromptTemplate:
    def test_structured_prompt_template_with_string_formatter(self) -> None:
        sections = [
            PromptSection(name="Introduction", content="This is an introduction"),
            PromptSection(name="Instructions", content="Follow these instructions"),
        ]
        prompt = StructuredPromptTemplate(sections=sections, formatter="string")
        expected = "\n".join(["Introduction", "This is an introduction", "Instructions", "Follow these instructions"])
        assert prompt.get_template() == expected
        assert isinstance(prompt._formatter_obj, StringPromptFormatter)

    def test_structured_prompt_template_with_markdown_formatter(self) -> None:
        sections = [
            PromptSection(name="Introduction", content="This is an introduction"),
            PromptSection(name="Instructions", content="Follow these instructions"),
        ]
        prompt = StructuredPromptTemplate(sections=sections, formatter="markdown")
        expected = "\n".join(
            ["# Introduction", "", "This is an introduction", "# Instructions", "", "Follow these instructions"]
        )
        assert prompt.get_template() == expected
        assert isinstance(prompt._formatter_obj, MarkdownPromptFormatter)

    def test_structured_prompt_template_with_xml_formatter(self) -> None:
        sections = [
            PromptSection(name="Introduction", content="This is an introduction"),
            PromptSection(name="Instructions", content="Follow these instructions"),
        ]
        prompt = StructuredPromptTemplate(sections=sections, formatter="xml")
        expected = "\n".join(
            [
                "<introduction>",
                "  This is an introduction",
                "</introduction>",
                "<instructions>",
                "  Follow these instructions",
                "</instructions>",
            ]
        )
        assert prompt.get_template() == expected
        assert isinstance(prompt._formatter_obj, XMLPromptFormatter)

    def test_nested_sections(self) -> None:
        sections = [
            PromptSection(
                name="Main Section",
                content="Main content",
                sections=[PromptSection(name="Subsection", content="Subsection content")],
            )
        ]

        prompt = StructuredPromptTemplate(sections=sections, formatter="string")
        expected_string = "\n".join(["Main Section", "Main content", "Subsection", "Subsection content"])
        assert prompt.get_template() == expected_string

        prompt.set_formatter(MarkdownPromptFormatter())
        expected_md = "\n".join(["# Main Section", "", "Main content", "## Subsection", "", "Subsection content"])
        assert prompt.get_template() == expected_md

        prompt.set_formatter(XMLPromptFormatter())
        expected_xml = "\n".join(
            [
                "<main_section>",
                "  Main content",
                "  <subsection>",
                "    Subsection content",
                "  </subsection>",
                "</main_section>",
            ]
        )
        assert prompt.get_template() == expected_xml

    def test_invalid_formatter(self) -> None:
        sections = [PromptSection(name="Test", content="Test content")]

        with pytest.raises(ValueError, match="Unknown formatter"):
            StructuredPromptTemplate(sections=sections, formatter="invalid_formatter")

    def test_set_formatter_manually(self) -> None:
        sections = [PromptSection(name="Test", content="Test content")]
        prompt = StructuredPromptTemplate(sections=sections)

        prompt.set_formatter(XMLPromptFormatter())
        assert isinstance(prompt._formatter_obj, XMLPromptFormatter)
        expected = "\n".join(["<test>", "  Test content", "</test>"])
        assert prompt.get_template() == expected


class TestPromptFormatters:
    def test_string_prompt_formatter_with_custom_prefix(self) -> None:
        formatter = StringPromptFormatter(section_prefix=">> ")
        sections = [
            PromptSection(name="Section1", content="Content1"),
            PromptSection(name="Section2", content="Content2"),
        ]
        expected = "\n".join([">> Section1", "Content1", ">> Section2", "Content2"])
        assert formatter.format(sections) == expected

    def test_markdown_formatter_nested_headings(self) -> None:
        formatter = MarkdownPromptFormatter()
        sections = [
            PromptSection(
                name="Level 1",
                content="Content 1",
                sections=[
                    PromptSection(
                        name="Level 2",
                        content="Content 2",
                        sections=[PromptSection(name="Level 3", content="Content 3")],
                    )
                ],
            )
        ]
        expected = "\n".join(
            ["# Level 1", "", "Content 1", "## Level 2", "", "Content 2", "### Level 3", "", "Content 3"]
        )
        assert formatter.format(sections) == expected

    def test_xml_formatter_multiline_content(self) -> None:
        formatter = XMLPromptFormatter()
        sections = [PromptSection(name="Section", content="Line 1\nLine 2\nLine 3")]
        expected = "\n".join(["<section>", "  Line 1", "  Line 2", "  Line 3", "</section>"])
        assert formatter.format(sections) == expected

    def test_formatter_registry(self) -> None:
        assert FORMATTER_REGISTRY["string"] == StringPromptFormatter
        assert FORMATTER_REGISTRY["markdown"] == MarkdownPromptFormatter
        assert FORMATTER_REGISTRY["xml"] == XMLPromptFormatter


class TestPromptPair:
    def test_prompt_pair_with_system_only(self) -> None:
        system_prompt = PromptTemplate(template="You are a helpful assistant.")
        pair = PromptPair(system=system_prompt)
        assert pair.system == system_prompt
        assert pair.user is None

    def test_prompt_pair_with_system_and_user(self) -> None:
        system_prompt = PromptTemplate(template="You are a helpful assistant.")
        user_prompt = PromptTemplate(template="Help me with {task}.")
        pair = PromptPair(system=system_prompt, user=user_prompt)
        assert pair.system == system_prompt
        assert pair.user == user_prompt


class TestStructuredPromptPair:
    def test_structured_prompt_pair_system_only(self) -> None:
        system_prompt = StructuredPromptTemplate(
            sections=[PromptSection(name="System", content="You are a helpful assistant.")]
        )
        pair = StructuredPromptPair(system=system_prompt)
        assert pair.system == system_prompt
        assert pair.user is None

    def test_structured_prompt_pair_with_system_and_user(self) -> None:
        system_prompt = StructuredPromptTemplate(
            sections=[PromptSection(name="System", content="You are a helpful assistant.")]
        )
        user_prompt = StructuredPromptTemplate(sections=[PromptSection(name="User", content="Help me with this task.")])
        pair = StructuredPromptPair(system=system_prompt, user=user_prompt)
        assert pair.system == system_prompt
        assert pair.user == user_prompt


class TestLLMConfig:
    def test_llm_config_with_model_only(self) -> None:
        config = LLMConfig(model="gpt-4o")
        assert config.model == "gpt-4o"
        assert config.params is None

    def test_llm_config_with_params(self) -> None:
        params = {"temperature": 0.7, "max_tokens": 100, "another_param": "value"}
        config = LLMConfig(model="gpt-4o", params=params)
        assert config.model == "gpt-4o"
        assert config.params == params


class TestPromptConfig:
    def test_prompt_config_initialization(self) -> None:
        prompt_pair = PromptPair(
            system=PromptTemplate(template="You are a helpful assistant."),
            user=PromptTemplate(template="Help me with {task}."),
        )
        metadata = {"version": "1.0", "author": "John Doe", "created_at": "2025-02-25"}

        config = PromptConfig(kind="Prompt", prompt=prompt_pair, metadata=metadata, llm=LLMConfig(model="gpt-4o"))

        assert config.kind == "Prompt"
        assert config.prompt == prompt_pair
        assert config.metadata == metadata
        assert config.llm is not None
        assert config.llm.model == "gpt-4o"

    def test_prompt_config_with_structured_prompt(self) -> None:
        system_prompt = StructuredPromptTemplate(
            sections=[PromptSection(name="System", content="You are a helpful assistant.")]
        )
        prompt_pair = StructuredPromptPair(system=system_prompt)

        config = PromptConfig(
            kind="StructuredPrompt", prompt=prompt_pair, metadata={"version": "1.0"}, llm=LLMConfig(model="gpt-4o")
        )

        assert config.kind == "StructuredPrompt"
        assert isinstance(config.prompt, StructuredPromptPair)
        assert config.has_llm_config is True

    def test_with_empty_metadata_and_llm(self) -> None:
        prompt_pair = PromptPair(
            system=PromptTemplate(template="You are a helpful assistant."),
            user=PromptTemplate(template="Help me with {task}."),
        )
        config = PromptConfig(kind="Prompt", prompt=prompt_pair)

        assert config.metadata is None
        assert config.llm is None

    def test_prompt_config_invalid_kind(self) -> None:
        system_prompt = PromptTemplate(template="You are a helpful assistant.")
        prompt_pair = PromptPair(system=system_prompt)

        with pytest.raises(ValidationError):
            PromptConfig(kind="InvalidKind", prompt=prompt_pair)  # type: ignore

    def test_mixed_prompt_pair_validation(self) -> None:
        system_prompt = PromptTemplate(template="System template")
        user_prompt = StructuredPromptTemplate(sections=[PromptSection(name="User", content="User content")])

        with pytest.raises(ValidationError):
            StructuredPromptPair(system=system_prompt, user=user_prompt)  # type: ignore

    def test_from_dict(self) -> None:
        data = {
            "kind": "Prompt",
            "prompt": {
                "system": {"template": "You are a helpful assistant."},
                "user": {"template": "Help me with this task."},
            },
            "metadata": {"version": "0.0.1"},
            "llm": {"model": "gpt-4o", "params": {"temperature": 0.7}},
        }

        config = PromptConfig(**data)  # type: ignore

        assert config.kind == "Prompt"
        assert isinstance(config.prompt, PromptPair)
        assert isinstance(config.prompt.system, PromptTemplate)
        assert config.prompt.system.template == "You are a helpful assistant."
        assert isinstance(config.prompt.user, PromptTemplate)
        assert config.prompt.user.template == "Help me with this task."
        assert config.metadata == {"version": "0.0.1"}
        assert config.llm is not None
        assert config.llm.model == "gpt-4o"
        assert config.llm.params == {"temperature": 0.7}

    def test_prompt_from_file(self) -> None:
        config = PromptConfig.from_yaml(PromptPath.basic)

        assert config.kind == "Prompt"
        assert isinstance(config.prompt, PromptPair)
        assert isinstance(config.prompt.system, PromptTemplate)
        assert config.prompt.system.get_template() == "You are a helpful assistant."
        assert isinstance(config.prompt.user, PromptTemplate)
        assert config.prompt.user.get_template() == "Answer the following questions: {question}"
        assert config.metadata == {"description": "This is a prompt doing abc\n"}
        assert config.has_llm_config is True
        assert config.llm is not None
        assert config.llm.model == "gpt-4o-mini"
        assert config.llm.params == {"temperature": 0.3}

    def test_structured_prompt_from_file(self) -> None:
        config = PromptConfig.from_yaml(PromptPath.structured)

        assert config.kind == "StructuredPrompt"
        assert isinstance(config.prompt, StructuredPromptPair)
        assert isinstance(config.prompt.system, StructuredPromptTemplate)
        assert config.prompt.system.get_template() == "\n".join(
            [
                "<instructions>",
                "  You are a helpful assistant.",
                "  <hints>",
                "    Answer the question in a concise manner.",
                "  </hints>",
                "</instructions>",
            ]
        )
        assert isinstance(config.prompt.user, StructuredPromptTemplate)
        assert config.prompt.user.get_template() == "\n".join(
            ["<question>", "  What's the capital of France?", "</question>"]
        )
        assert config.metadata == {"description": "This is a prompt doing xyz\n"}
        assert config.has_llm_config is True
        assert config.llm is not None
        assert config.llm.model == "claude-3-5-haiku-20241022"
        assert config.llm.params == {"temperature": 0.2}
