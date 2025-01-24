from hexbytes import HexBytes
from unittest.mock import Mock, patch

from alphaswarm.config import Config
from alphaswarm.exchanges.uniswap.uniswap import UniswapClientV3


@patch("alphaswarm.exchanges.uniswap.uniswap.create_multi_provider_web3")
def test_get_final_swap_amount_received(mock_create_web3):
    # Create a real swap receipt with Transfer events
    mock_receipt = {
        "transactionHash": HexBytes("0x6d604a9e64704dc13651d32eb75245fac72eacecfb2a9e090f6e3d2dd93b22a4"),
        "blockHash": HexBytes("0x8d14059d62f4577d5e7f22b19c3c901fa21d33281f9d3b385b19a80088bc854e"),
        "blockNumber": 21634587,
        "logs": [
            {
                # USDC Transfer
                "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                "data": HexBytes("0x000000000000000000000000000000000000000000000000000000000033746a"),
                "topics": [
                    HexBytes("0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"),
                    HexBytes("0x000000000000000000000000e0554a476a092703abdb3ef35c80e0d76d32939f"),
                    HexBytes("0x000000000000000000000000cc825866e8bb5a3a9746f3ea32a2380c64a2c210"),
                ],
            },
            {
                # WETH Transfer
                "address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "data": HexBytes("0x00000000000000000000000000000000000000000000000000038d7ea4c68000"),
                "topics": [
                    HexBytes("0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"),
                    HexBytes("0x000000000000000000000000cc825866e8bb5a3a9746f3ea32a2380c64a2c210"),
                    HexBytes("0x000000000000000000000000e0554a476a092703abdb3ef35c80e0d76d32939f"),
                ],
            },
        ],
        "status": 1,
    }

    # Create a mock config
    mock_config = Mock(spec=Config)
    mock_config.values = {
        "chain_config": {"ethereum": {"chain_id": 1, "tokens": {}}},
        "trading_venues": {"uniswap_v3": {"settings": {"fee_tiers": [500, 3000, 10000]}}},
    }

    # Mock the chain config
    mock_chain_config = Mock()
    mock_chain_config.rpc_url = "https://eth-mainnet.alchemyapi.io/v2/your-api-key"  # This won't be used in the test
    mock_config.get_chain_config = Mock(return_value=mock_chain_config)

    # Mock Web3
    mock_web3 = Mock()
    mock_create_web3.return_value = mock_web3

    client = UniswapClientV3(mock_config, "ethereum")

    # Test getting USDC amount received (user receives USDC)
    usdc_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    user_address = "0xcC825866E8bB5A3A9746F3EA32A2380c64a2C210"
    usdc_decimals = 6

    usdc_amount = client._get_final_swap_amount_received(mock_receipt, usdc_address, user_address, usdc_decimals)

    # Expected amount: 0x33746a = 3372138 raw amount = 3.372138 USDC
    expected_usdc = 3.372138
    assert abs(usdc_amount - expected_usdc) < 0.00001, f"Expected {expected_usdc} USDC but got {usdc_amount}"

    # Test getting WETH amount sent (user sends WETH)
    weth_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    weth_decimals = 18

    weth_amount = client._get_final_swap_amount_received(mock_receipt, weth_address, user_address, weth_decimals)

    # Expected amount: 0 WETH (since user is sending, not receiving)
    assert weth_amount == 0, f"Expected 0 WETH but got {weth_amount}"
