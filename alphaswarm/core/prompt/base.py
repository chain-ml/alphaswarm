from __future__ import annotations

import abc

from pydantic import BaseModel


class PromptTemplateBase(BaseModel, abc.ABC):
    @abc.abstractmethod
    def get_template(self) -> str:
        pass

# TODO: base prompt pair
