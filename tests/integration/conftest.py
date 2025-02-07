import time
from _pytest.fixtures import fixture
import pytest

from alphaswarm.config import Config
from alphaswarm.services.alchemy import AlchemyClient
from alphaswarm.services.cookiefun import CookieFunClient
from tests.unit.conftest import default_config

__all__ = ["default_config"]


@fixture
def alchemy_client(default_config: Config) -> AlchemyClient:
    # this helps with rate limit
    time.sleep(1)
    return AlchemyClient.from_env()


@pytest.fixture
def cookiefun_client(default_config: Config) -> CookieFunClient:
    """Create CookieFun client for testing"""
    return CookieFunClient()
