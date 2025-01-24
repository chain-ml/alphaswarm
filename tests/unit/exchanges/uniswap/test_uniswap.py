from decimal import Decimal

import pytest

from alphaswarm.config import Config
from alphaswarm.exchanges.factory import DEXFactory
from alphaswarm.exchanges.uniswap.uniswap import UniswapClientV2, UniswapClientV3


@pytest.mark.skip(reason="need to find a reasonable pool")
def test_get_price_v3(default_config: Config):
    ## Uniswap pool: https://app.uniswap.org/explore/pools/ethereum_sepolia/0xD7822b5A41c3655c6C403167F6B8Aa1533620329
    config = default_config
    chain = "ethereum_sepolia"
    swap = DEXFactory.create("uniswap_v3", default_config, chain)
    token_in = config.get_token_info(chain=chain, token="USDC")
    token_out = config.get_token_info(chain=chain, token="WETH")
    result1 = swap.get_token_price(base_token=token_out, quote_token=token_in)
    result2 = swap.get_token_price(base_token=token_in, quote_token=token_out)

    assert result1 is not None
    assert result2 is not None
    print(f"1 {token_in.symbol} is {result1} {token_out.symbol}")
    print(f"1 {token_out.symbol} is {1/result1} {token_in.symbol}")

    assert result1 > 0
    assert result2 > 0
    assert result1 < 1, "USDC is a fraction of WETH"

    assert pytest.approx(result1, Decimal(0.001)) == 1 / result2


def test_base_v3_pool(default_config: Config):
    config = default_config
    chain = "base"
    swap: UniswapClientV3 = DEXFactory.create("uniswap_v3", default_config, chain)  # type: ignore
    token_in = config.get_token_info(chain=chain, token="USDC")
    token_out = config.get_token_info(chain=chain, token="AIXBT")
    result = swap._get_v3_pool(base_token=token_in, quote_token=token_out)

    assert result is not None
    assert result.address.lower() == "0xf1Fdc83c3A336bdbDC9fB06e318B08EadDC82FF4".lower()
    assert {token_in.address.lower(), token_out.address.lower()} == {
        result.token0.address.lower(),
        result.token1.address.lower(),
    }


def test_get_markets_for_tokens_v2(default_config: Config):
    """Test getting markets between USDC and WETH on Uniswap V2."""
    chain = "ethereum"
    client: UniswapClientV2 = DEXFactory.create("uniswap_v2", default_config, chain)  # type: ignore

    # Get token info from addresses directly since they might not be in config
    usdc_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"  # Ethereum USDC
    weth_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"  # Ethereum WETH

    web3_client = client._blockchain_client
    usdc = web3_client.get_token_info(usdc_address, chain)
    weth = web3_client.get_token_info(weth_address, chain)

    # Check if we got valid token info
    assert usdc is not None, "Failed to get USDC token info"
    assert weth is not None, "Failed to get WETH token info"

    tokens = [usdc, weth]
    markets = client.get_markets_for_tokens(tokens)

    assert markets is not None
    assert len(markets) > 0  # Should find at least one market

    # Check first market pair
    base_token, quote_token = markets[0]
    assert {base_token.symbol, quote_token.symbol} == {"USDC", "WETH"}
    assert base_token.chain == chain
    assert quote_token.chain == chain


def test_get_markets_for_tokens_v3(default_config: Config):
    """Test getting markets between USDC and WETH on Uniswap V3."""
    chain = "ethereum"
    client: UniswapClientV3 = DEXFactory.create("uniswap_v3", default_config, chain)  # type: ignore

    # Get token info from addresses directly since they might not be in config
    usdc_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"  # Ethereum USDC
    weth_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"  # Ethereum WETH

    web3_client = client._blockchain_client
    usdc = web3_client.get_token_info(usdc_address, chain)
    weth = web3_client.get_token_info(weth_address, chain)

    # Check if we got valid token info
    assert usdc is not None, "Failed to get USDC token info"
    assert weth is not None, "Failed to get WETH token info"

    tokens = [usdc, weth]
    markets = client.get_markets_for_tokens(tokens)

    assert markets is not None
    assert len(markets) > 0  # Should find at least one market

    # Check first market pair
    base_token, quote_token = markets[0]
    assert {base_token.symbol, quote_token.symbol} == {"USDC", "WETH"}
    assert base_token.chain == chain
    assert quote_token.chain == chain
