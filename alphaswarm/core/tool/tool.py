from textwrap import dedent
from typing import Any, Dict, Optional, Sequence, get_type_hints

from pydantic import BaseModel
from smolagents import Tool


class AlphaSwarmTool:
    """
    An AlphaSwarm Tool being used by AlphaSwarm Agents.

    Automatically sets the following attributes if not already provided:
    - name: being class name
    - description: being docstring of the class
        + description of the output type schema if forward() returns BaseModel
        + usage examples if any
    - output_type: if forward() returns BaseModel or string
    """

    name: str
    """The name of the tool."""

    description: str
    """The description of the tool."""

    inputs: Dict[str, Dict[str, Any]] = {}
    """The input parameters schema of the tool."""

    output_type: str
    """The type of the tool's output."""

    examples: Sequence[str] = ()
    """The usage examples of the tool."""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        cls.name = cls._construct_name()
        cls.description = cls._construct_description()

    def forward(self, *args: Any, **kwargs: Any) -> Any:
        """The tool implementation."""
        raise NotImplementedError

    @classmethod
    def _construct_name(cls) -> str:
        """Construct the name of the tool - returns name attribute if provided, otherwise class name."""
        if "name" in cls.__dict__:
            return cls.name
        return cls.__name__

    @classmethod
    def _construct_description(cls) -> str:
        """
        Construct the full description of the tool, combining base description, output type description and examples.
        """
        description_parts = [cls._get_base_description()]

        output_type_description = cls._get_output_type_description()
        if output_type_description is not None:
            description_parts.append(output_type_description)
        if len(cls.examples) > 0:
            description_parts.append(cls._format_examples(cls.examples))

        return "\n\n".join(description_parts).strip()

    @classmethod
    def _get_base_description(cls) -> str:
        """Get the base description of the tool - returns description attribute if provided, otherwise docstring."""
        if "description" in cls.__dict__:
            return cls.description
        if cls.__doc__ is not None:
            return dedent(cls.__doc__).strip()

        raise ValueError("Description of the tool must be provided either as a class attribute or docstring")

    @classmethod
    def _get_output_type_description(cls) -> Optional[str]:
        """
        Get a description of the return type schema when forward() returns a BaseModel or string
        and automatically sets output_type attribute for these cases.
        """
        hints = get_type_hints(cls.forward)
        output_type = hints.get("return")

        if isinstance(output_type, type) and issubclass(output_type, BaseModel):
            cls.output_type = "object"
            # could add additional hints after the schema for AlphaSwarmToolInput class?
            return (
                f"Returns a {output_type.__name__} object with the following schema:\n\n"
                f"{output_type.model_json_schema()}"
            )
        elif output_type is str:
            cls.output_type = "string"
            return "Returns a string"
        # support more types

        return None

    @staticmethod
    def _format_examples(examples: Sequence[str]) -> str:
        return "Examples:\n" + "\n".join(f"- {example}" for example in examples)

    def to_smolagents(self) -> Tool:
        return Tool(name=self.name, description=self.description, inputs=self.inputs, output_type=self.output_type)
