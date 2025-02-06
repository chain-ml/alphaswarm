from decimal import Decimal

import pytest

from alphaswarm.config import Config, TokenInfo
from alphaswarm.services.exchanges.uniswap import UniswapClientV3

BASE_WETH_USDC_005 = "0xd0b53D9277642d899DF5C87A3966A349A798F224"


@pytest.fixture
def base_client(default_config: Config) -> UniswapClientV3:
    return UniswapClientV3(default_config, chain="base")


@pytest.fixture
def eth_client(default_config: Config) -> UniswapClientV3:
    return UniswapClientV3(default_config, chain="ethereum")


@pytest.fixture
def eth_sepolia_client(default_config: Config) -> UniswapClientV3:
    return UniswapClientV3(default_config, chain="ethereum_sepolia")


def test_get_price(base_client: UniswapClientV3) -> None:
    token0 = base_client.chain_config.get_token_info("USDC")
    token1 = base_client.chain_config.get_token_info("WETH")
    token1_per_token0 = base_client.get_token_price(base_token=token1, quote_token=token0)

    print(f"1 {token1.symbol} is {token1_per_token0} {token0.symbol}")


def test_quote_from_pool(base_client: UniswapClientV3) -> None:
    pool = base_client._get_pool_by_address(BASE_WETH_USDC_005)
    usdc: TokenInfo = base_client.chain_config.get_token_info("USDC")
    weth = base_client.chain_config.get_token_info("WETH")

    price_in_usdc = pool.get_price_for_token_out(usdc.checksum_address)
    print(f"1 {weth.symbol} is {price_in_usdc} {usdc.symbol}")

    price_in_weth = pool.get_price_for_token_in(usdc.checksum_address)
    print(f"1 {usdc.symbol} is {price_in_weth} {weth.symbol}")

    assert price_in_usdc > price_in_weth


def test_get_pool_detail(base_client: UniswapClientV3) -> None:
    pool = base_client._get_pool_by_address(BASE_WETH_USDC_005)

    assert pool.address == BASE_WETH_USDC_005
    assert pool._pool_details.token0.symbol == "WETH"
    assert pool._pool_details.token1.symbol == "USDC"
    assert pool._pool_details.token0.address == base_client.chain_config.get_token_info("WETH").address
    assert pool._pool_details.token1.address == base_client.chain_config.get_token_info("USDC").address


def test_get_pool_for_token_pair(base_client: UniswapClientV3) -> None:
    usdc = base_client.chain_config.get_token_info("USDC")
    weth = base_client.chain_config.get_token_info("WETH")
    pool = base_client._get_pool(usdc, weth)

    assert pool.address == BASE_WETH_USDC_005


def test_get_markets_for_tokens(eth_client: UniswapClientV3) -> None:
    """Test getting markets between USDC and WETH on Uniswap V3."""
    # Get token info from addresses directly since they might not be in config
    usdc_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"  # Ethereum USDC
    weth_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"  # Ethereum WETH

    evm_client = eth_client._evm_client
    usdc = evm_client.get_token_info(evm_client.to_checksum_address(usdc_address))
    weth = evm_client.get_token_info(evm_client.to_checksum_address(weth_address))

    tokens = [usdc, weth]
    markets = eth_client.get_markets_for_tokens(tokens)

    assert markets is not None
    assert len(markets) > 0  # Should find at least one market

    # Check first market pair
    base_token, quote_token = markets[0]
    assert {base_token.symbol, quote_token.symbol} == {"USDC", "WETH"}
    assert base_token.chain == eth_client.chain
    assert quote_token.chain == eth_client.chain


@pytest.mark.skip("Needs a wallet with USDC to perform the swap to WETH. Run manually")
def test_swap_eth_sepolia(eth_sepolia_client: UniswapClientV3) -> None:
    usdc = eth_sepolia_client.chain_config.get_token_info("USDC")
    weth = eth_sepolia_client.chain_config.get_token_info("WETH")

    pool = eth_sepolia_client._get_pool(usdc, weth)
    print(f"find pool {pool.address}")

    quote = eth_sepolia_client._get_token_price_from_pool(quote_token=usdc, pool_details=pool)
    print(f"1 {weth.symbol} is {quote} {usdc.symbol}")

    # Buy X Weth for 1 USDC
    result = eth_sepolia_client.swap(weth, usdc, Decimal(1))
    print(result)
