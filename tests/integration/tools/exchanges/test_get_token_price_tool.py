from alphaswarm.tools.exchanges import GetTokenPriceTool
from alphaswarm.config import Config


def test_get_token_price_tool(default_config: Config) -> None:
    config = default_config
    tool = GetTokenPriceTool(config)
    result = tool.forward(base_token="VIRTUAL", quote_token="WETH", dex_type="uniswap_v3", chain="base")

    assert len(result.prices) > 0
