import time

from _pytest.fixtures import fixture

from alphaswarm.config import Config
from alphaswarm.services.alchemy import AlchemyClient
from tests.unit.conftest import default_config

__all__ = ["default_config"]


@fixture
def alchemy_client(default_config: Config) -> AlchemyClient:
    # this helps with rate limit
    time.sleep(1)
    return AlchemyClient.from_env()
