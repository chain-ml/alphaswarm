from typing import Any, Dict, Literal, List, Type

from pydantic import BaseModel, Field

from alphaswarm.core.llm import with_reasoning


def schema_properties(schema: Type[BaseModel]) -> Dict[str, Any]:
    return schema.model_json_schema()["properties"]


def schema_properties_keys(schema: Type[BaseModel]) -> List[str]:
    return list(schema.model_json_schema()["properties"].keys())


def test_with_reasoning_default_description() -> None:
    @with_reasoning()
    class Model(BaseModel):
        a: float = Field(..., description="Parameter a")
        b: float = Field(3.14, description="Parameter b")

    class ExpectedModel(BaseModel):
        reasoning: str = Field(..., description="Your reasoning to arrive at the answer")
        a: float = Field(..., description="Parameter a")
        b: float = Field(3.14, description="Parameter b")

    assert schema_properties(Model) == schema_properties(ExpectedModel)


def test_with_reasoning_custom_description() -> None:
    @with_reasoning(description="Custom reasoning description")
    class Model(BaseModel):
        other: Literal["a", "b", "c"] = Field(..., description="Other field")

    class ExpectedModel(BaseModel):
        reasoning: str = Field(..., description="Custom reasoning description")
        other: Literal["a", "b", "c"] = Field(..., description="Other field")

    assert schema_properties(Model) == schema_properties(ExpectedModel)


def test_with_reasoning_field_order() -> None:
    @with_reasoning()
    class Model(BaseModel):
        a: float = Field(..., description="First field")
        b: str = Field(..., description="Second field")
        c: int = Field(..., description="Third field")

    properties = schema_properties_keys(Model)

    assert properties[0] == "reasoning"
    assert properties[1:] == ["a", "b", "c"]


def test_with_reasoning_nested_fields() -> None:
    @with_reasoning()
    class NestedModel(BaseModel):
        x: int = Field(..., description="Nested field")

    @with_reasoning()
    class Model(BaseModel):
        nested: NestedModel
        other: str = Field(..., description="Other field")

    properties = schema_properties_keys(Model)
    nested_properties = schema_properties_keys(NestedModel)
    assert properties == ["reasoning", "nested", "other"]
    assert nested_properties == ["reasoning", "x"]
