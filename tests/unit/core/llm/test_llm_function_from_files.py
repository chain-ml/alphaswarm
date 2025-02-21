import tempfile
from typing import Any

import pytest
from pydantic import BaseModel

from alphaswarm.core.llm import LLMFunctionTemplated


class Response(BaseModel):
    test: str


def get_sample_llm_function_from_files(**kwargs: Any) -> LLMFunctionTemplated[Response]:
    return LLMFunctionTemplated.from_files(
        model_id="test",
        response_model=Response,
        **kwargs,
    )


def test_execute_with_user_prompt_params_but_no_template_raises() -> None:
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".txt", delete=True) as system_file:
        system_file.write("Sample system prompt")
        system_file.flush()

        llm_func = get_sample_llm_function_from_files(system_prompt_path=system_file.name)

    with pytest.raises(ValueError, match="User prompt params provided but no user prompt template exists"):
        llm_func.execute(user_prompt_params={"test": "value"})
