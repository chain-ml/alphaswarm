import logging

from alphaswarm.config import Config
from alphaswarm.services.exchanges.uniswap.constants_v2 import UNISWAP_V2_DEPLOYMENTS, UNISWAP_V2_INIT_CODE_HASH
from alphaswarm.services.exchanges.uniswap.uniswap_client import UniswapClient

logger = logging.getLogger(__name__)


class UniswapClientV2(UniswapClient):
    def __init__(self, config: Config, chain: str):
        super().__init__(config, chain, "v2")

    def _initialize(self) -> bool:
        if self.version == "v2" and self.chain in UNISWAP_V2_DEPLOYMENTS:  # Check for V2 support
            deployment_data_v2 = UNISWAP_V2_DEPLOYMENTS[self.chain]
            init_code_hash = UNISWAP_V2_INIT_CODE_HASH.get(self.chain)
            if not init_code_hash:
                raise ValueError(f"No V2 init code hash found for chain: {self.chain}")

            logger.info(f"Initializing Uniswap V2 on {self.chain} with:")
            logger.info(f"  Factory: {deployment_data_v2['factory']}")
            logger.info(f"  Router: {deployment_data_v2['router']}")
            logger.info(f"  Init Code Hash: {init_code_hash}")

            self._factory = deployment_data_v2["factory"]
            self._router = deployment_data_v2["router"]
            return True

        return False
