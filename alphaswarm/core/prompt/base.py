import abc
from typing import Annotated, Generic, Optional, TypeVar

from pydantic import BaseModel, StringConstraints

# helper class alias for str that's automatically stripped
StrippedStr = Annotated[str, StringConstraints(strip_whitespace=True)]


class PromptTemplateBase(BaseModel, abc.ABC):
    @abc.abstractmethod
    def get_template(self) -> str:
        pass


T = TypeVar("T", bound="BaseModel")


class PromptPairBase(BaseModel, Generic[T]):
    system: T
    user: Optional[T] = None
