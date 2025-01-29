from datetime import datetime, timedelta, timezone
from alphaswarm.services.alchemy.alchemy_client import AlchemyClient


def test_historical_prices_by_symbol(alchemy_client: AlchemyClient):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=1)
    result = alchemy_client.get_historical_prices_by_symbol(
        symbol="USDC", start_time=start, end_time=end, interval="1h"
    )

    assert result is not None
    assert result.symbol == "USDC"
    assert len(result.data) == 24
    assert result.data[0].value > 0.1
    assert result.data[0].timestamp >= start


def test_historical_prices_by_address(alchemy_client: AlchemyClient):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=1)
    address = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
    network = "eth-mainnet"
    result = alchemy_client.get_historical_prices_by_address(
        address=address, network=network, start_time=start, end_time=end, interval="1h"
    )

    assert result is not None
    assert result.address == address
    assert result.network == network
    assert len(result.data) == 24
    assert result.data[0].value > 0.1
    assert result.data[0].timestamp >= start
