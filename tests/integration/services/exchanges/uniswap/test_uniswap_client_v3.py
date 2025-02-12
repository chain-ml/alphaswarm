from decimal import Decimal

import pytest

from alphaswarm.config import Config, TokenInfo
from alphaswarm.services.exchanges.uniswap import UniswapClientV3

BASE_WETH_USDC_005 = "0xd0b53D9277642d899DF5C87A3966A349A798F224"


@pytest.fixture
def base_client(default_config: Config) -> UniswapClientV3:
    chain_config = default_config.get_chain_config(chain="base")
    return UniswapClientV3(chain_config=chain_config, settings=default_config.get_venue_settings_uniswap_v3())


@pytest.fixture
def eth_client(default_config: Config) -> UniswapClientV3:
    chain_config = default_config.get_chain_config(chain="ethereum")
    return UniswapClientV3(chain_config=chain_config, settings=default_config.get_venue_settings_uniswap_v3())


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


@pytest.fixture
def client(default_config: Config, chain: str) -> UniswapClientV3:
    return UniswapClientV3.from_config(default_config, chain)


chains = [
    "ethereum",
    "ethereum_sepolia",
    "base",
    # "base_sepolia",
]


@pytest.mark.parametrize("chain", chains)
def test_quote_weth_to_usdc(client: UniswapClientV3, chain: str) -> None:
    usdc = client.chain_config.get_token_info("USDC")
    weth = client.chain_config.get_token_info("WETH")
    quote = client.get_token_price(token_out=usdc, token_in=weth, amount_in=Decimal("0.01"))
    print(quote)
    assert 10_000 > quote.amount_out > 10


@pytest.mark.skip("Need a funded wallet.")
@pytest.mark.parametrize("chain", chains)
def test_swap_weth_to_usdc(client: UniswapClientV3, chain: str) -> None:
    usdc = client.chain_config.get_token_info("USDC")
    weth = client.chain_config.get_token_info("WETH")
    amount_in = Decimal("0.0001")

    quote = client.get_token_price(token_out=usdc, token_in=weth, amount_in=amount_in)
    assert quote.amount_out > amount_in, "1 USDC is worth a fraction of WETH"

    result = client.swap(quote)
    print(result)
    assert result.success
    assert result.amount_in == amount_in
    assert result.amount_out == pytest.approx(quote.amount_out, rel=Decimal("0.05"))
