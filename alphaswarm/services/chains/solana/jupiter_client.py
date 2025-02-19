from typing import Annotated, Any, Final, List, Optional

import requests
from alphaswarm.services import ApiException
from pydantic import Field
from pydantic.dataclasses import dataclass


@dataclass
class JupiterTokenInfo:
    address: str
    created_at: str
    daily_volume: Annotated[Optional[float], Field(default=None)]
    decimals: int
    extensions: Any
    freeze_authority: Annotated[Optional[str], Field(default=None)]
    logo_uri: Annotated[Optional[str], Field(alias="logoURI", default=None)]
    mint_authority: Annotated[str, Field(default=None)]
    minted_at: Annotated[Optional[str], Field(default=None)]
    name: str
    symbol: str
    permanent_delegate: Annotated[Optional[str], Field(default=None)]
    tags: Annotated[List[str], Field(default_factory=list)]


class JupiterClient:
    BASE_URL: Final[str] = "https://api.jup.ag/"
    TOKEN_URL: Final[str] = "https://api.jup.ag/tokens/v1/token/{address}"

    def get_token_info(self, token_address: str) -> JupiterTokenInfo:
        response = requests.get(self.TOKEN_URL.format(address=token_address))
        if response.status_code != 200:
            raise ApiException(response)

        return JupiterTokenInfo(**response.json())
