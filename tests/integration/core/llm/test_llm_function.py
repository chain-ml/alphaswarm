import time
from typing import List, Literal, Type

import dotenv
from pydantic import BaseModel, Field

from alphaswarm.core.llm import LLMFunction, ImageURL, Message
from tests import get_data_filename

dotenv.load_dotenv()


class TestResponse(BaseModel):
    content: str = Field(..., description="The content of the response")


class SimpleResponse(BaseModel):
    reasoning: str = Field(..., description="Reasoning behind the response")
    number: int = Field(..., ge=1, le=10, description="The random number between 1 and 10.")


class ItemPricePair(BaseModel):
    item: str = Field(..., description="The item name")
    price: float = Field(..., ge=0, description="The price of the item")


class ComplexResponse(BaseModel):
    store: str = Field(..., description="The name of the store")
    category: Literal["food", "clothing", "electronics", "other"] = Field(..., description="The category of the store")
    list_of_items: List[ItemPricePair] = Field(..., description="The list of items and their prices")


def get_llm_function(response_model: Type[BaseModel] = SimpleResponse, **kwargs) -> LLMFunction:
    return LLMFunction(
        model_id="anthropic/claude-3-haiku-20240307",
        response_model=response_model,
        **kwargs,
    )


def test_llm_function_simple():
    llm_func = get_llm_function(system_message="Output a random number between 1 and 10")

    result = llm_func.execute()
    assert isinstance(result, SimpleResponse)
    assert 1 <= result.number <= 10


def test_llm_function_messages():
    llm_func = get_llm_function(
        system_message="Output a random number",
        messages=[Message.create(role="user", content="Pick between 2 and 5")],
    )

    result = llm_func.execute()
    assert isinstance(result, SimpleResponse)
    assert 2 <= result.number <= 5


def test_llm_function_user_message():
    llm_func = get_llm_function(system_message="Output a random number")

    result = llm_func.execute(user_message="Pick between 3 and 7")
    assert isinstance(result, SimpleResponse)
    assert 3 <= result.number <= 7


def test_llm_function_with_complex_response_model():
    llm_func = get_llm_function(
        response_model=ComplexResponse,
        system_message="Output a list of items and their prices for a made up store",
    )
    result = llm_func.execute()
    assert isinstance(result, ComplexResponse)
    assert isinstance(result.store, str)
    assert result.category in ["food", "clothing", "electronics", "other"]
    assert all(isinstance(item, ItemPricePair) for item in result.list_of_items)


def test_llm_function_with_prompt_caching():
    large_content = "Paris is capital of France" * 300  # caching from 2k tokens for haiku
    llm_func = LLMFunction(
        model_id="anthropic/claude-3-haiku-20240307",
        response_model=TestResponse,
        messages=[Message.system(large_content, cache=True)],
    )

    llm_func_response = llm_func.execute_with_completion("What's the capital of France?")
    assert isinstance(llm_func_response.response, TestResponse)
    assert "Paris" in llm_func_response.response.content

    time.sleep(1)

    llm_func_response = llm_func.execute_with_completion("What's the capital of France?")
    assert isinstance(llm_func_response.response, TestResponse)
    assert "Paris" in llm_func_response.response.content

    assert llm_func_response.completion.usage.prompt_tokens_details.cached_tokens > 0


def test_llm_function_with_image():
    message = Message.create(
        role="user", content="Describe the image", image_url=ImageURL.from_path(get_data_filename("eth_sol_prices.png"))
    )
    llm_func = get_llm_function(response_model=TestResponse, messages=[message])

    result = llm_func.execute()
    assert isinstance(result, TestResponse)
    assert "eth" in result.content.lower()
    assert "sol" in result.content.lower()
