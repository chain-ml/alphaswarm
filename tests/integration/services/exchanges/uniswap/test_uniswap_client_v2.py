from alphaswarm.config import Config
from alphaswarm.services.exchanges import DEXFactory
from alphaswarm.services.exchanges.uniswap import UniswapClientV2


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

    tokens = [usdc, weth]
    markets = client.get_markets_for_tokens(tokens)

    assert markets is not None
    assert len(markets) > 0  # Should find at least one market

    # Check first market pair
    base_token, quote_token = markets[0]
    assert {base_token.symbol, quote_token.symbol} == {"USDC", "WETH"}
    assert base_token.chain == chain
    assert quote_token.chain == chain
