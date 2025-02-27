from __future__ import annotations

import abc
from typing import Any, Optional

from pydantic import BaseModel


class PromptTemplateBase(BaseModel, abc.ABC):
    @abc.abstractmethod
    def get_template(self) -> str:
        pass


class PromptPairBase(BaseModel):
    system: Any
    user: Optional[Any] = None
