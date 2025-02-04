from decimal import Decimal

import pytest
from eth_typing import BlockNumber, HexStr
from hexbytes import HexBytes
from web3 import Web3
from web3.types import TxReceipt, Wei

from alphaswarm.services.chains import EVMClient
from alphaswarm.services.chains.evm import ZERO_ADDRESS
from alphaswarm.services.exchanges.uniswap import UniswapClientV3


@pytest.fixture
def mock_receipt() -> TxReceipt:
    return {
        "transactionHash": HexBytes("0x6d604a9e64704dc13651d32eb75245fac72eacecfb2a9e090f6e3d2dd93b22a4"),
        "blockHash": HexBytes("0x8d14059d62f4577d5e7f22b19c3c901fa21d33281f9d3b385b19a80088bc854e"),
        "blockNumber": BlockNumber(21634587),
        "logs": [
            {
                # USDC Transfer
                "address": Web3.to_checksum_address("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"),
                "data": HexBytes("0x000000000000000000000000000000000000000000000000000000000033746a"),
                "topics": [
                    HexBytes("0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"),
                    HexBytes("0x000000000000000000000000e0554a476a092703abdb3ef35c80e0d76d32939f"),
                    HexBytes("0x000000000000000000000000cc825866e8bb5a3a9746f3ea32a2380c64a2c210"),
                ],
                "blockHash": HexBytes(0),
                "blockNumber": BlockNumber(0),
                "logIndex": 0,
                "transactionHash": HexBytes(0),
                "transactionIndex": 0,
                "removed": False,
            },
            {
                # WETH Transfer
                "address": Web3.to_checksum_address("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"),
                "data": HexBytes("0x00000000000000000000000000000000000000000000000000038d7ea4c68000"),
                "topics": [
                    HexBytes("0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"),
                    HexBytes("0x000000000000000000000000cc825866e8bb5a3a9746f3ea32a2380c64a2c210"),
                    HexBytes("0x000000000000000000000000e0554a476a092703abdb3ef35c80e0d76d32939f"),
                ],
                "blockHash": HexBytes(0),
                "blockNumber": BlockNumber(0),
                "logIndex": 0,
                "transactionHash": HexBytes(0),
                "transactionIndex": 0,
                "removed": False,
            },
        ],
        "status": 1,
        ## Additional fields
        "contractAddress": None,
        "cumulativeGasUsed": 0,
        "effectiveGasPrice": Wei(0),
        "gasUsed": 0,
        "from": Web3.to_checksum_address(ZERO_ADDRESS),
        "logsBloom": HexBytes(0),
        "root": HexStr("0x12"),
        "to": Web3.to_checksum_address(ZERO_ADDRESS),
        "transactionIndex": 0,
        "type": 0,
    }


def test_get_final_swap_amount_received_usdc(mock_receipt: TxReceipt) -> None:
    # Test getting USDC amount received (user receives USDC)
    usdc_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    user_address = "0xcC825866E8bB5A3A9746F3EA32A2380c64a2C210"
    usdc_decimals = 6

    usdc_amount = UniswapClientV3._get_final_swap_amount_received(
        mock_receipt, EVMClient.to_checksum_address(usdc_address), user_address, usdc_decimals
    )

    # Expected amount: 0x33746a = 3372138 raw amount = 3.372138 USDC
    expected_usdc = Decimal("3.372138")
    assert abs(usdc_amount - expected_usdc) < Decimal("0.00001"), f"Expected {expected_usdc} USDC but got {usdc_amount}"


def test_get_final_swap_amount_received_weth(mock_receipt: TxReceipt) -> None:
    # Test getting WETH amount sent (user sends WETH)
    weth_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    user_address = "0xcC825866E8bB5A3A9746F3EA32A2380c64a2C210"
    weth_decimals = 18

    weth_amount = UniswapClientV3._get_final_swap_amount_received(
        mock_receipt, EVMClient.to_checksum_address(weth_address), user_address, weth_decimals
    )

    # Expected amount: 0 WETH (since user is sending, not receiving)
    assert weth_amount == 0, f"Expected 0 WETH but got {weth_amount}"
