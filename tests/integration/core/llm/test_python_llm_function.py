from typing import List

import dotenv
from pydantic import BaseModel
from alphaswarm.core.llm.llm_function import PythonLLMFunction, LLMFunctionInput

dotenv.load_dotenv()


class PersonInput(LLMFunctionInput):
    name: str
    age: int

    def to_prompt(self) -> str:
        return (
            f"Suggest a backstory for a person named {self.name} who is {self.age} years old. "
            f"Keep it in 50 words or less."
        )


class PersonBackstory(LLMFunctionInput):
    backstory: str

    def to_prompt(self) -> str:
        return f"Suggest top 5 hobbies for a person with the following backstory: {self.backstory}."


class HobbySuggestion(BaseModel):
    hobbies: List[str]


def get_person_to_backstory_function() -> PythonLLMFunction[PersonBackstory]:
    return PythonLLMFunction(model_id="gpt-4o", response_model=PersonBackstory)


def get_backstory_to_hobbies_function() -> PythonLLMFunction[HobbySuggestion]:
    return PythonLLMFunction(model_id="gpt-4o", response_model=HobbySuggestion)


def test_python_llm_function() -> None:
    person_to_backstory_function = get_person_to_backstory_function()

    input_obj = PersonInput(name="John", age=48)
    backstory_response = person_to_backstory_function.execute(input_obj)
    assert isinstance(backstory_response, PersonBackstory)
    assert isinstance(backstory_response.backstory, str)


def test_chained_llm_functions() -> None:
    person_to_backstory_function = get_person_to_backstory_function()
    backstory_to_hobbies_function = get_backstory_to_hobbies_function()

    input_obj = PersonInput(name="Martha", age=32)
    backstory_response = person_to_backstory_function.execute(input_obj)
    assert isinstance(backstory_response, PersonBackstory)

    hobby_response = backstory_to_hobbies_function.execute(backstory_response)
    assert isinstance(hobby_response, HobbySuggestion)
    assert len(hobby_response.hobbies) > 0
