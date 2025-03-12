import abc
from typing import Annotated, Any, Optional

from pydantic import BaseModel, StringConstraints

# helper class alias for str that's automatically stripped
StrippedStr = Annotated[str, StringConstraints(strip_whitespace=True)]


class PromptTemplateBase(BaseModel, abc.ABC):
    @abc.abstractmethod
    def get_template(self) -> str:
        pass


class PromptPairBase(BaseModel):
    system: Any
    user: Optional[Any] = None
