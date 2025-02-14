from typing import Dict, Any

import pytest
from pydantic import BaseModel, Field
from alphaswarm.core.tool import AlphaSwarmTool


def test_base() -> None:
    class MyTool(AlphaSwarmTool):
        """This is my tool description"""

        def forward(self) -> None:
            raise NotImplementedError

    my_tool = MyTool()

    assert my_tool.name == "MyTool"
    assert my_tool.description == "This is my tool description"


def test_multiline_description() -> None:
    class MyTool(AlphaSwarmTool):
        """
        This is my multiline
        tool description
        """

        def forward(self) -> None:
            raise NotImplementedError

    my_tool = MyTool()

    assert my_tool.name == "MyTool"
    assert my_tool.description == "This is my multiline\ntool description"


def test_missing_description() -> None:
    with pytest.raises(ValueError) as e:

        class MyTool(AlphaSwarmTool):
            def forward(self) -> None:
                raise NotImplementedError

    assert str(e.value) == "Description of the tool must be provided either as a class attribute or docstring"


def test_override() -> None:
    class MyTool(AlphaSwarmTool):
        """This is my tool description"""

        name = "MyTool2"
        description = "This is my tool description v2"
        inputs: Dict[str, Any] = {}
        output_type = "string"

        def forward(self) -> None:
            raise NotImplementedError

    my_tool = MyTool()

    assert my_tool.name == "MyTool2"
    assert my_tool.description == "This is my tool description v2"
    assert my_tool.output_type == "string"


def test_output_type_base_model() -> None:
    class MyModel(BaseModel):
        name: str = Field(..., description="The name of the person")
        age: int = Field(..., description="The age of the person")

    class MyTool(AlphaSwarmTool):
        """This is my tool description"""

        def forward(self) -> MyModel:
            raise NotImplementedError

    my_tool = MyTool()

    assert my_tool.output_type == "object"
    assert my_tool.description.startswith("This is my tool description")
    assert "Returns a MyModel object with the following schema:" in my_tool.description
    assert "The name of the person" in my_tool.description
    assert "The age of the person" in my_tool.description


def test_with_examples() -> None:
    class MyTool(AlphaSwarmTool):
        """This is my tool description"""

        examples = ["Example 1", "Example 2"]

        def forward(self) -> None:
            raise NotImplementedError

    my_tool = MyTool()

    assert my_tool.description.startswith("This is my tool description")
    assert "Examples:" in my_tool.description
    assert "Example 1" in my_tool.description
    assert "Example 2" in my_tool.description
