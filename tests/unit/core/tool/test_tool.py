from typing import Tuple

import pytest
from pydantic import BaseModel, Field
from alphaswarm.core.tool import AlphaSwarmToolBase
from smolagents import Tool

from alphaswarm.core.tool.tool import AlphaSwarmToSmolAgentsToolAdapter


def alphaswarm_tool_and_smolagents_tool(tool: AlphaSwarmToolBase) -> Tuple[AlphaSwarmToolBase, Tool]:
    return tool, AlphaSwarmToSmolAgentsToolAdapter.adapt(tool)


def test_base() -> None:
    class MyTool(AlphaSwarmToolBase):
        """This is my tool description"""

        def forward(self) -> None:
            raise NotImplementedError

    tool, smolagents_tool = alphaswarm_tool_and_smolagents_tool(MyTool())
    assert tool.name == smolagents_tool.name == "MyTool"
    assert tool.description == smolagents_tool.description == "This is my tool description"
    assert tool.output_type is type(None)
    assert smolagents_tool.output_type == "null"


def test_multiline_description() -> None:
    class MyTool(AlphaSwarmToolBase):
        """
        This is my multiline
        tool description
        """

        def forward(self) -> str:
            raise NotImplementedError

    tool, smolagents_tool = alphaswarm_tool_and_smolagents_tool(MyTool())
    assert tool.name == smolagents_tool.name == "MyTool"
    assert tool.description == smolagents_tool.description == "This is my multiline\ntool description"
    assert tool.output_type is str
    assert smolagents_tool.output_type == "string"


def test_missing_description() -> None:
    with pytest.raises(ValueError) as e:

        class MyTool(AlphaSwarmToolBase):
            def forward(self) -> None:
                raise NotImplementedError

    assert str(e.value) == "Description of the tool must be provided either as a class attribute or docstring"


def test_override() -> None:
    class MyTool(AlphaSwarmToolBase):
        """This is my tool description"""

        name = "MyTool2"
        description = "This is my tool description v2"
        output_type = int

        def forward(self) -> None:
            raise NotImplementedError

    tool, smolagents_tool = alphaswarm_tool_and_smolagents_tool(MyTool())
    assert tool.name == smolagents_tool.name == "MyTool2"
    assert tool.description == smolagents_tool.description == "This is my tool description v2"
    assert tool.output_type is int
    assert smolagents_tool.output_type == "integer"


def test_output_type_base_model() -> None:
    class MyModel(BaseModel):
        name: str = Field(..., description="The name of the person")
        age: int = Field(..., description="The age of the person")

    class MyTool(AlphaSwarmToolBase):
        """This is my BaseModel tool description"""

        def forward(self) -> MyModel:
            raise NotImplementedError

    tool, smolagents_tool = alphaswarm_tool_and_smolagents_tool(MyTool())
    for t in [tool, smolagents_tool]:
        assert t.description.startswith("This is my BaseModel tool description")
        assert "Returns a MyModel object with the following schema:" in t.description
        assert "The name of the person" in t.description
        assert "The age of the person" in t.description

    assert tool.output_type is MyModel
    assert smolagents_tool.output_type == "object"


def test_with_examples() -> None:
    class MyTool(AlphaSwarmToolBase):
        """This is my tool description"""

        examples = ["Examples:", "- Example 1", "- Example 2"]

        def forward(self) -> float:
            raise NotImplementedError

    tool, smolagents_tool = alphaswarm_tool_and_smolagents_tool(MyTool())
    for t in [tool, smolagents_tool]:
        assert t.description.startswith("This is my tool description")
        for example in MyTool.examples:
            assert example in t.description

    assert tool.output_type is float
    assert smolagents_tool.output_type == "number"


def test_incorrect_inputs_descriptions() -> None:
    with pytest.raises(ValueError) as e:

        class MyTool(AlphaSwarmToolBase):
            """This is my tool description"""

            def forward(self, a: str, b) -> None:  # type: ignore
                raise NotImplementedError

    assert str(e.value) == "Missing type hints for forward() method parameters: b"

    with pytest.raises(ValueError) as e:

        class MyTool_v2(AlphaSwarmToolBase):
            """This is my tool description"""

            def forward(self, a: str, b: int) -> None:
                raise NotImplementedError

    assert str(e.value) == "Missing docstring for the forward() method. Must contain parameters descriptions."

    with pytest.raises(ValueError) as e:

        class MyTool_v3(AlphaSwarmToolBase):
            """This is my tool description"""

            def forward(self, a: str, b: int) -> None:
                """This is a docstring"""
                raise NotImplementedError

    assert str(e.value) == "Missing Args/Parameters section in the forward() method docstring."

    with pytest.raises(ValueError) as e:

        class MyTool_v4(AlphaSwarmToolBase):
            """This is my tool description"""

            def forward(self, a: str, b: int) -> None:
                """
                Args:
                    a: This is a description for a
                """
                raise NotImplementedError

    assert str(e.value) == "Missing description for parameters: b"


def test_inputs_descriptions() -> None:
    class MyTool(AlphaSwarmToolBase):
        """This is my tool description"""

        def forward(self, a: str, b: int) -> None:
            """
            Args:
                a: This is a description for a
                b: This is a description for b
            """
            raise NotImplementedError

    tool, smolagents_tool = alphaswarm_tool_and_smolagents_tool(MyTool())
    assert tool.inputs_descriptions == {"a": "This is a description for a", "b": "This is a description for b"}
    assert smolagents_tool.inputs == {
        "a": {"description": "This is a description for a", "type": "string"},
        "b": {"description": "This is a description for b", "type": "integer"},
    }


@pytest.mark.skip("Not implemented yet.")
def test_multiline_inputs_descriptions() -> None:
    class MyTool(AlphaSwarmToolBase):
        """This is my tool description"""

        def forward(self, a: str, b: int) -> None:
            """
            Args:
                a: This is a multiline
                    description for a
                b: This is a description for b
            """
            raise NotImplementedError

    my_tool = MyTool()
    assert my_tool.inputs_descriptions == {
        "a": "This is a multiline\ndescription for a",
        "b": "This is a description for b",
    }
