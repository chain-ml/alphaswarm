from decimal import Decimal
from typing import Optional, Union

from alphaswarm.config import TokenInfo
from alphaswarm.services.chains.evm.constants_erc20 import ERC20_ABI
from eth_typing import ChecksumAddress
from web3.contract import Contract
from web3.types import TxReceipt, Wei

from .evm import EVMClient, EVMSigner


class EVMContract:
    def __init__(self, client: EVMClient, address: ChecksumAddress, abi: list[dict]):
        self._client = client
        self._address = address
        self._abi = abi
        self._contract = client.get_contract(address=address, abi=abi)

    @property
    def contract(self) -> Contract:
        return self._contract

    @property
    def address(self) -> ChecksumAddress:
        return self._address


class ERC20Contract(EVMContract):
    def __init__(self, client: EVMClient, address: ChecksumAddress) -> None:
        super().__init__(client, address, ERC20_ABI)
        self._details: Optional[TokenInfo] = None

    @property
    def details(self) -> TokenInfo:
        if self._details is None:
            details = self._client.get_token_details(self._address)
            self._details = TokenInfo(
                symbol=details.symbol,
                decimals=details.decimals,
                address=details.address,
                chain=self._client.chain,
                is_native=False,
            )
        return self._details

    def get_balance(self, owner: ChecksumAddress) -> Decimal:
        return self.contract.functions.balanceOf(owner).call()

    def get_allowance(self, owner: ChecksumAddress, spender: ChecksumAddress) -> Wei:
        return self.contract.functions.allowance(owner, spender).call()

    def get_allowance_token(self, owner: ChecksumAddress, spender: ChecksumAddress) -> Decimal:
        return self.details.convert_from_wei(self.get_allowance(owner, spender))

    def approve_token(self, signer: EVMSigner, spender: ChecksumAddress, value: Decimal) -> TxReceipt:
        return self.approve(signer, spender, self.details.convert_to_wei(value))

    def approve(self, signer: EVMSigner, spender: ChecksumAddress, value: Union[Wei, int]) -> TxReceipt:
        return self._client.process(self.contract.functions.approve(spender, value), signer)
