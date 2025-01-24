import os

import dotenv
from _pytest.fixtures import fixture

from alphaswarm.config import Config


@fixture
def default_config() -> Config:
    base_path = os.path.join(os.path.dirname(__file__), "..", "..")
    env_file = os.path.join(base_path, ".env")
    if os.path.isfile(env_file):
        dotenv.load_dotenv(env_file)

    env_example = os.path.join(base_path, ".env.example")
    assert os.path.isfile(env_example)
    dotenv.load_dotenv(env_example)

    return Config(network_env="all")
