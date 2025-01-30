import tempfile

import dotenv
from pydantic import BaseModel, Field

from alphaswarm.core.llm import LLMFunctionFromPromptFiles

dotenv.load_dotenv()


class SimpleResponse(BaseModel):
    reasoning: str = Field(..., description="Reasoning behind the response")
    number: int = Field(..., ge=1, le=10, description="The random number between 1 and 10.")


def get_llm_function_from_files(**kwargs) -> LLMFunctionFromPromptFiles[SimpleResponse]:
    return LLMFunctionFromPromptFiles(
        model_id="anthropic/claude-3-haiku-20240307",
        response_model=SimpleResponse,
        **kwargs,
    )


def test_llm_function_from_system_file():
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".txt", delete=True) as temp_file:
        temp_file.write("Output a random number between {min_value} and {max_value}")
        temp_file.flush()  # ensure the content is written to disk

        llm_func = get_llm_function_from_files(
            system_prompt_path=temp_file.name,
            system_prompt_params={"min_value": 2, "max_value": 7},
        )
        result = llm_func.execute()
        assert isinstance(result, SimpleResponse)
        assert 2 <= result.number <= 7


def test_llm_function_from_user_file():
    with (
        tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".txt", delete=True) as system_file,
        tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".txt", delete=True) as user_file,
    ):
        system_file.write("You are a number generator that follows user instructions")
        system_file.flush()

        user_file.write("Generate a number between {min_value} and {max_value}")
        user_file.flush()

        llm_func = get_llm_function_from_files(
            system_prompt_path=system_file.name,
            user_prompt_path=user_file.name,
        )

        result = llm_func.execute(user_prompt_params={"min_value": 3, "max_value": 8})
        assert isinstance(result, SimpleResponse)
        assert 3 <= result.number <= 8
