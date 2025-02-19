import abc
import inspect
from textwrap import dedent
from typing import Any, Dict, Optional, Sequence, Type, Union, get_args, get_origin, get_type_hints

from pydantic import BaseModel
from smolagents import Tool


class AlphaSwarmToolBase(abc.ABC):
    """
    An AlphaSwarm Tool being used by AlphaSwarm Agents.
    """

    name: str
    """
    The name of the tool. 
    Will be automatically set to class name if not provided.
    """

    description: str
    """
    The description of the tool, automatically set to docstring of the class if not provided.
    Will be automatically extended with the output type description if the forward() method returns a BaseModel
    and examples if any are provided.
    """

    examples: Sequence[str]
    """The usage examples of the tool."""

    inputs_descriptions: Dict[str, str]
    """
    Mapping of forward() parameter names to their descriptions. 
    Will be derived from the forward() method docstring if not provided.
    """

    output_type: Type
    """forward() output type. Will derived from the function signature if not provided."""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        cls.name = cls._construct_name()
        cls.inputs_descriptions = cls._construct_inputs_descriptions()
        cls.output_type = cls._construct_output_type()
        cls.description = cls._construct_description()

    @abc.abstractmethod
    def forward(self, *args: Any, **kwargs: Any) -> Any:
        """The tool implementation."""
        pass

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
        if "examples" in cls.__dict__ and len(cls.examples) > 0:
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
        """Get a description of the return type schema when forward() returns a BaseModel."""

        if issubclass(cls.output_type, BaseModel):
            # could add additional hints after the schema for AlphaSwarmToolInput class? or object docstring?
            return (
                f"Returns a {cls.output_type.__name__} object with the following schema:\n\n"
                f"{cls.output_type.model_json_schema()}"
            )

        return None

    @staticmethod
    def _format_examples(examples: Sequence[str]) -> str:
        return "Examples:\n" + "\n".join(f"- {example}" for example in examples)

    @classmethod
    def _construct_inputs_descriptions(cls) -> Dict[str, str]:
        """
        Construct the inputs descriptions
        Returns inputs_descriptions attribute if provided, otherwise extract from forward() method docstring.
        """
        if "inputs_descriptions" in cls.__dict__:
            return cls.inputs_descriptions

        forward_signature = inspect.signature(cls.forward)
        params = [param for param in forward_signature.parameters.keys() if param != "self"]

        if not params:
            return {}

        hints = get_type_hints(cls.forward)
        params_hints = {param: t for param, t in hints.items() if param != "return"}

        missing_hints = [param for param in params if param not in params_hints]
        if missing_hints:
            raise ValueError(f"Missing type hints for forward() method parameters: {', '.join(missing_hints)}")

        docstring = cls.forward.__doc__
        if not docstring:
            raise ValueError("Missing docstring for the forward() method. Must contain parameters descriptions.")

        docstring = dedent(docstring).strip()
        lines = docstring.splitlines()

        # find the Args/Parameters section
        section_start = None
        for i, line in enumerate(lines):
            if line.strip() in ("Args:", "Parameters:"):
                section_start = i + 1
                break

        if section_start is None:
            raise ValueError("Missing Args/Parameters section in the forward() method docstring.")

        inputs_descriptions: Dict[str, str] = {}

        for line in lines[section_start:]:
            stripped_line = line.strip()

            # expect each parameter line to follow: <param>: <description>
            if ":" not in stripped_line:
                continue

            param_name, description = stripped_line.split(":", 1)
            param_name = param_name.strip()
            description = description.strip()
            inputs_descriptions[param_name] = description

        missing_descriptions = [param for param in params if param not in inputs_descriptions]
        if missing_descriptions:
            raise ValueError(f"Missing description for parameters: {', '.join(missing_descriptions)}")

        return inputs_descriptions

    @classmethod
    def _construct_output_type(cls) -> Type:
        """
        Construct the output type
        Returns output_type attribute if provided, otherwise forward() return type from type hints.
        """
        if "output_type" in cls.__dict__:
            return cls.output_type

        hints = get_type_hints(cls.forward)
        output_type = hints.get("return")
        if output_type is None:
            raise ValueError("Missing return type hint for the forward() method")

        if not isinstance(output_type, type):
            raise RuntimeError("forward() output type hint is not a type")

        return output_type


class AlphaSwarmToSmolAgentsToolAdapter:
    """Adapter class to convert AlphaSwarmToolBase instances to smolagents Tool instances."""

    @classmethod
    def adapt(cls, alphaswarm_tool: AlphaSwarmToolBase) -> Tool:
        tool = Tool()

        tool.name = alphaswarm_tool.name
        tool.description = alphaswarm_tool.description
        tool.inputs = cls._construct_smolagents_inputs(alphaswarm_tool)
        tool.output_type = cls._get_smolagents_type(alphaswarm_tool.output_type)
        tool.forward = alphaswarm_tool.forward

        return tool

    @classmethod
    def _construct_smolagents_inputs(cls, alphaswarm_tool: AlphaSwarmToolBase) -> Dict[str, Any]:
        hints = get_type_hints(alphaswarm_tool.forward)

        inputs = {
            name: {"description": description, "type": cls._get_smolagents_type(hints[name])}
            for name, description in alphaswarm_tool.inputs_descriptions.items()
        }
        return inputs

    @staticmethod
    def _get_smolagents_type(t: Type) -> str:
        types_to_smolagents_types = {
            str: "string",
            bool: "boolean",
            int: "integer",
            float: "number",
            type(None): "null",
        }

        # handling Optional[type]
        origin = get_origin(t)
        if origin is Union:
            args = get_args(t)
            non_none_args = [arg for arg in args if arg is not type(None)]
            if len(non_none_args) == 1:
                return types_to_smolagents_types.get(non_none_args[0], "object")

        return types_to_smolagents_types.get(t, "object")
