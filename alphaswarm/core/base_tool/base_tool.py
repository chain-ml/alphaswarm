from textwrap import dedent
from typing import Any

from smolagents import Tool


class AlphaSwarmBaseTool(Tool):
    """
    A wrapper around the smolagents tool interface.

    Automatically sets the following attributes if not already provided:
    - name: being class name
    - description: being docstring of the class
    - output_type: being "object"
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        if "name" not in cls.__dict__:
            cls.name = cls.__name__
        if "description" not in cls.__dict__:
            if cls.__doc__ is None:
                raise ValueError("Description of the tool must be provided either as docstring or as a class attribute")
            cls.description = dedent(cls.__doc__).strip()
        if "output_type" not in cls.__dict__:
            cls.output_type = "object"
