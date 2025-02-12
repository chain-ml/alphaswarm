from alphaswarm.config import Config
from alphaswarm.services.chains import EVMClient


def test_get_token_info(default_config: Config) -> None:
    """Test getting token info for USDC on ethereum."""
    chain = "ethereum"
    client = EVMClient(chain_config=default_config.get_chain_config(chain))
    usdc_address = EVMClient.to_checksum_address("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")

    token_info = client.get_token_info(usdc_address)
    print(token_info)

    assert token_info.address == usdc_address
    assert token_info.decimals == 6
    assert token_info.symbol == "USDC"
    assert token_info.chain == chain
    assert not token_info.is_native
