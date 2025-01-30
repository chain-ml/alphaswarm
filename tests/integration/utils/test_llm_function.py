from typing import List, Literal, Type

import dotenv
from pydantic import BaseModel, Field

from alphaswarm.utils import LLMFunction

dotenv.load_dotenv()


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
        model_id="gpt-4o",
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
        messages=[{"role": "user", "content": "Pick between 2 and 5"}],
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
