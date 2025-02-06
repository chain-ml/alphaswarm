from typing import Type, get_type_hints, Any, List, Dict, Union, Optional
from types import GenericAlias
import inspect
from decimal import Decimal
from datetime import datetime

def get_class_description(cls: Type) -> str:
    """Extract description from class docstring."""
    if cls.__doc__:
        return inspect.cleandoc(cls.__doc__).split("\n")[0]
    return ""

def format_type(typ: Any) -> tuple[str, set[Type]]:
    """Format a type hint into a readable string and collect nested types."""
    nested_types = set()
    
    # Handle Lists
    if hasattr(typ, "__origin__") and typ.__origin__ is list:
        inner_type = typ.__args__[0]
        # Don't show full module path, just the class name
        if hasattr(inner_type, "__name__"):
            type_name = inner_type.__name__
            nested_types.add(inner_type)
        else:
            type_name = str(inner_type)
        return f"List[{type_name}]", nested_types
    
    # Handle basic types
    if typ in {str, int, float, Decimal, datetime}:
        return typ.__name__, nested_types
    
    # Handle classes
    if inspect.isclass(typ):
        return typ.__name__, {typ}
    
    return str(typ), nested_types

def generate_type_schema(cls: Type) -> str:
    """Generate schema description for a class and its nested types."""
    described_types = set()
    basic_types = {str, int, float, bool, Decimal, datetime}
    
    def get_field_description(typ: Type, field_name: str) -> str:
        """Extract field description from either dataclass Field or Pydantic Field."""
        # Check for dataclass Field
        if hasattr(typ, "__dataclass_fields__"):
            field = typ.__dataclass_fields__[field_name]
            if hasattr(field, "metadata"):
                if "description" in field.metadata and field.metadata["description"]:
                    return f" - {field.metadata['description']}"
                elif hasattr(field.default, "description") and field.default.description:
                    return f" - {field.default.description}"
        
        # Check for Pydantic model Field
        if hasattr(typ, "model_fields"):  # Pydantic v2
            if field_name in typ.model_fields:
                field = typ.model_fields[field_name]
                if field.description:
                    return f" - {field.description}"
        elif hasattr(typ, "__fields__"):  # Pydantic v1
            if field_name in typ.__fields__:
                field = typ.__fields__[field_name]
                if field.field_info.description:
                    return f" - {field.field_info.description}"
        
        return ""
    
    def _describe_type(typ: Type, indent: int = 0) -> List[str]:
        if typ in described_types or typ in basic_types:
            return []
        
        described_types.add(typ)
        indent_str = "    " * indent
        lines = [f"{indent_str}Schema for {typ.__name__}:"]
        
        # Get type hints
        hints = get_type_hints(typ)
        
        # Add field descriptions
        nested_to_describe = set()
        for name, field_type in hints.items():
            type_str, nested = format_type(field_type)
            nested_to_describe.update(n for n in nested if n not in basic_types)
            
            # Get field description
            field_desc = get_field_description(typ, name)
            
            # Only append description if it's not empty
            line = f"{indent_str}- {name}: {type_str}"
            if field_desc:
                line += field_desc
            lines.append(line)
        
        # Add descriptions for nested types
        for nested_type in nested_to_describe:
            if nested_type not in described_types and nested_type != typ:
                lines.extend([""] + _describe_type(nested_type, indent + 1))
        
        return lines
    
    return "\n".join(_describe_type(cls))

def with_return_type_schema(return_type: Type):
    """
    Decorator to inject schema description into Tool description.
    Works with any Python class that has type hints.
    """
    def decorator(cls):
        base_description = cls.description
        schema_description = generate_type_schema(return_type)
        
        cls.description = f"""{base_description}

Return Type Details:
{schema_description}
"""
        return cls
    return decorator