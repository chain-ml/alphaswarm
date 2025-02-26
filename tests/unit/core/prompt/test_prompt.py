import pytest
from alphaswarm.core.prompt import PromptConfig
from alphaswarm.core.prompt.prompt import (
    PromptTemplate,
    PromptPair,
    LLMConfig,
)
from tests import PromptPath


class TestPromptTemplate:
    def test_prompt_template(self) -> None:
        template = "This is a test template with {variable}"
        prompt = PromptTemplate(template=template)
        assert prompt.template == template


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

        with pytest.raises(ValueError, match="Invalid kind: InvalidKind"):
            PromptConfig(kind="InvalidKind", prompt=prompt_pair)

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

    def test_from_file(self) -> None:
        config = PromptConfig.from_yaml(PromptPath.basic)

        assert config.kind == "Prompt"
        assert isinstance(config.prompt, PromptPair)
        assert isinstance(config.prompt.system, PromptTemplate)
        assert config.prompt.system.template == "You are a helpful assistant."
        assert isinstance(config.prompt.user, PromptTemplate)
        assert config.prompt.user.template == "Answer the following questions: {question}"
        assert config.metadata == {"description": "This is a prompt doing abc\n"}
        assert config.llm is not None
        assert config.llm.model == "gpt-4o-mini"
        assert config.llm.params == {"temperature": 0.3}
