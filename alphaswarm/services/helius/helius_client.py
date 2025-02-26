import os
from typing import Dict, Final, List, Self, Sequence

import requests
from alphaswarm.services import ApiException

from .data import EnhancedTransaction, SignatureResult


class HeliusClient:
    BASE_RPC_URL: Final[str] = "https://mainnet.helius-rpc.com"
    BASE_TRANSACTION_URL: Final[str] = "https://api.helius.xyz"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def _make_request(self, url: str, data: Dict) -> Dict:
        params = {"api-key": self._api_key}
        response = requests.post(url=url, json=data, params=params)
        if response.status_code >= 400:
            raise ApiException(response)
        return response.json()

    def get_signatures_for_address(self, wallet_address: str) -> List[SignatureResult]:
        body = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "getSignaturesForAddress",
            "params": [
                wallet_address,
            ],
        }

        response = self._make_request(self.BASE_RPC_URL, body)
        return [SignatureResult(**item) for item in response["result"]]

    def get_transactions(self, signatures: Sequence[str]) -> List[EnhancedTransaction]:
        if len(signatures) > 100:
            raise ValueError("Can only get 100 transactions at a time")

        data = {"transactions": signatures}
        response = self._make_request(f"{self.BASE_TRANSACTION_URL}/v0/transactions", data)
        return [EnhancedTransaction(**item) for item in response]

    @classmethod
    def from_env(cls) -> Self:
        return cls(api_key=os.environ["HELIUS_API_KEY"])
