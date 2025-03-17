from typing import Callable, Optional, Type, TypeVar

from pydantic import BaseModel, Field, create_model

T = TypeVar("T", bound=BaseModel)


def with_reasoning(description: Optional[str] = None) -> Callable[[Type[T]], Type[T]]:
    """
    Decorator that adds a 'reasoning' field to a Pydantic model to support Chain-of-Thought pattern.
    The reasoning field will be placed first in the schema.
    """

    def decorator(cls: Type[T]) -> Type[T]:
        original_fields = cls.__annotations__.copy()

        new_fields = {"reasoning": (str, Field(description=description or "Your reasoning to arrive at the answer"))}

        for field_name, field_type in original_fields.items():
            new_fields[field_name] = (
                field_type,
                cls.model_fields[field_name] if field_name in cls.model_fields else None,
            )

        return create_model(cls.__name__, __doc__=cls.__doc__, **new_fields)  # type: ignore

    return decorator
