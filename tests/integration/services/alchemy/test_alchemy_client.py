from datetime import datetime, timedelta, timezone

from _pytest.fixtures import fixture

from alphaswarm.config import Config
from alphaswarm.services.alchemy.alchemy_client import AlchemyClient


@fixture
def client(default_config: Config):
    return AlchemyClient(config=default_config)

def test_client(client: AlchemyClient):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=1)
    result = client.get_historical_prices(token="USDC", start_time=start, end_time=end, interval="1h", chain="base")

    assert result is not None
    assert len(result) == 24
    assert result[0].value > 0.1
    assert result[0].timestamp >= start
