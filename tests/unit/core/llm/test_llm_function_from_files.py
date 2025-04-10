import tempfile

import pytest
from pydantic import BaseModel

from alphaswarm.core.llm import LLMFunctionTemplated
from alphaswarm.core.prompt import PromptConfig

from tests import PromptPath


class Response(BaseModel):
    test: str


def test_execute_with_user_prompt_params_but_no_template_raises() -> None:
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".txt", delete=True) as system_file:
        system_file.write("Sample system prompt")
        system_file.flush()

        llm_func = LLMFunctionTemplated.from_files(
            model_id="test",
            response_model=Response,
            system_prompt_path=system_file.name,
        )

    with pytest.raises(ValueError, match="User prompt params provided but no user prompt template exists"):
        llm_func.execute(user_prompt_params={"test": "value"})


def test_from_prompt_config() -> None:
    llm_func_v1 = LLMFunctionTemplated.from_prompt_config(
        response_model=Response,
        prompt_config=PromptConfig.from_yaml(PromptPath.basic),
    )

    llm_func_v2 = LLMFunctionTemplated.from_prompt_config_file(
        response_model=Response,
        prompt_config_path=PromptPath.basic,
    )

    assert llm_func_v1._model_id == llm_func_v2._model_id == "gpt-4o-mini"
    assert llm_func_v1.system_prompt == llm_func_v2.system_prompt == "You are a helpful assistant."
    expected_user_prompt = "Answer the following questions: {question}"
    assert llm_func_v1.user_prompt_template == llm_func_v2.user_prompt_template == expected_user_prompt


def test_from_structured_prompt_config() -> None:
    llm_func = LLMFunctionTemplated.from_prompt_config_file(
        response_model=Response,
        prompt_config_path=PromptPath.structured,
    )

    assert llm_func._model_id == "claude-3-5-haiku-20241022"
    expected_system_prompt = "\n".join(
        [
            "<instructions>",
            "  You are a helpful assistant.",
            "  <hints>",
            "    Answer the question in a concise manner.",
            "  </hints>",
            "</instructions>",
        ]
    )
    assert llm_func.system_prompt == expected_system_prompt

    expected_user_prompt = "\n".join(
        [
            "<question>",
            "  What's the capital of France?",
            "</question>",
        ]
    )
    assert llm_func.user_prompt_template == expected_user_prompt
