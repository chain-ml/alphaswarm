from typing import Annotated, Any, Final, List, Optional

import requests
from alphaswarm.config import TokenInfo
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

    def to_token_info(self) -> TokenInfo:
        return TokenInfo(symbol=self.symbol, decimals=self.decimals, address=self.address, chain="solana")


class JupiterClient:
    BASE_URL: Final[str] = "https://api.jup.ag"
    TOKEN_URL: Final[str] = f"{BASE_URL}/tokens/v1/token/{{address}}"
    PRICE_URL: Final[str] = f"{BASE_URL}/price/v2"

    def get_token_info(self, token_address: str) -> JupiterTokenInfo:
        response = requests.get(self.TOKEN_URL.format(address=token_address))
        if response.status_code != 200:
            raise ApiException(response)

        return JupiterTokenInfo(**response.json())

    def get_token_price(self, id: str) -> JupiterTokenInfo:
        data = { "ids": id }
        response = requests.get(self.PRICE_URL, params=data)
        if response.status_code != 200:
            raise ApiException(response)

        return response.json()


