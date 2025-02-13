from typing import Dict, Any

import pytest

from alphaswarm.core.base_tool import AlphaSwarmBaseTool


def test_base() -> None:
    class MyTool(AlphaSwarmBaseTool):
        """This is my tool description"""

        inputs: Dict[str, Any] = {}

        def forward(self) -> None:
            return None

    my_tool = MyTool()

    assert my_tool.name == "MyTool"
    assert my_tool.description == "This is my tool description"
    assert my_tool.output_type == "object"


def test_multiline_description() -> None:
    class MyTool(AlphaSwarmBaseTool):
        """
        This is my multiline
        tool description
        """

        inputs: Dict[str, Any] = {}

        def forward(self) -> None:
            return None

    my_tool = MyTool()

    assert my_tool.name == "MyTool"
    assert my_tool.description == "This is my multiline\ntool description"
    assert my_tool.output_type == "object"


def test_missing_description() -> None:
    with pytest.raises(ValueError) as e:

        class MyTool(AlphaSwarmBaseTool):
            inputs: Dict[str, Any] = {}

            def forward(self) -> None:
                return None

    assert str(e.value) == "Description of the tool must be provided either as docstring or as a class attribute"


def test_override() -> None:
    class MyTool(AlphaSwarmBaseTool):
        """This is my tool description"""

        name = "MyTool2"
        description = "This is my tool description v2"
        inputs: Dict[str, Any] = {}
        output_type = "string"

        def forward(self) -> None:
            return None

    my_tool = MyTool()

    assert my_tool.name == "MyTool2"
    assert my_tool.description == "This is my tool description v2"
    assert my_tool.output_type == "string"
