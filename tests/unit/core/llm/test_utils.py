from pydantic import BaseModel, Field

from alphaswarm.core.llm import with_reasoning


def test_with_reasoning() -> None:
    @with_reasoning
    class Schema(BaseModel):
        a: float = Field(..., description="Parameter a")
        b: float = Field(3.14, description="Parameter b")

    class ExpectedSchema(BaseModel):
        reasoning: str = Field(..., description="Your reasoning to arrive at the answer")
        a: float = Field(..., description="Parameter a")
        b: float = Field(3.14, description="Parameter b")

    print(Schema.model_json_schema())
    print(ExpectedSchema.model_json_schema())
    assert Schema.model_json_schema()["properties"] == ExpectedSchema.model_json_schema()["properties"]
