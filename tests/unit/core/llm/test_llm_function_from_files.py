import tempfile

import pytest
from pydantic import BaseModel

from alphaswarm.core.llm import LLMFunctionFromPromptFiles, Message


class Response(BaseModel):
    test: str


def get_sample_llm_function_from_files(**kwargs) -> LLMFunctionFromPromptFiles[Response]:
    return LLMFunctionFromPromptFiles(
        model_id="test",
        response_model=Response,
        **kwargs,
    )


def test_execute_with_user_messages_raises():
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".txt", delete=True) as system_file:
        system_file.write("Sample system prompt")
        system_file.flush()

        llm_func = get_sample_llm_function_from_files(system_prompt_path=system_file.name)

    with pytest.raises(ValueError, match="Both `user_message` and `messages` are expected to be None"):
        llm_func.execute(user_message="test")

    with pytest.raises(ValueError, match="Both `user_message` and `messages` are expected to be None"):
        llm_func.execute(messages=[Message(role="user", content="test")])

    with pytest.raises(ValueError, match="Both `user_message` and `messages` are expected to be None"):
        llm_func.execute(user_message="test", messages=[Message(role="user", content="test")])


def test_execute_with_user_prompt_params_but_no_template_raises() -> None:
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".txt", delete=True) as system_file:
        system_file.write("Sample system prompt")
        system_file.flush()

        llm_func = get_sample_llm_function_from_files(system_prompt_path=system_file.name)

    with pytest.raises(ValueError, match="User prompt params provided but no user prompt template exists"):
        llm_func.execute(user_prompt_params={"test": "value"})
