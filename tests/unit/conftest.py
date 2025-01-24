import os

import dotenv
from _pytest.fixtures import fixture

from alphaswarm.config import Config


@fixture
def default_config() -> Config:
    file = os.path.join(os.path.dirname(__file__), "..", "..", ".env.example")
    assert os.path.isfile(file)
    dotenv.load_dotenv(file)
    return Config(network_env="all")
