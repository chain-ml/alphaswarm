from typing import Any

from smolagents import Tool


class AlphaSwarmBaseTool(Tool):
    """
    A wrapper around the smolagents tool interface.

    Automatically sets the following attributes:
    - name: being class name
    - description: being docstring of the class
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls.name = cls.__name__
        cls.description = cls.__doc__
        # TODO: only set if not provided?

        # cls.output_type = "object"  # next step
