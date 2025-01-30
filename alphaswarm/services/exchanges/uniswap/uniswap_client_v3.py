import logging

from alphaswarm.config import Config
from alphaswarm.services.exchanges.uniswap.constants_v3 import UNISWAP_V3_DEPLOYMENTS
from alphaswarm.services.exchanges.uniswap.uniswap_client import UniswapClient

logger = logging.getLogger(__name__)


class UniswapClientV3(UniswapClient):
    def __init__(self, config: Config, chain: str):
        super().__init__(config, chain, "v3")

    def _initialize(self) -> bool:
        if self.chain in UNISWAP_V3_DEPLOYMENTS:  # Check for V3 support
            deployment_data_v3 = UNISWAP_V3_DEPLOYMENTS[self.chain]

            logger.info(f"Initializing Uniswap V3 on {self.chain} with:")
            logger.info(f"  Factory: {deployment_data_v3['factory']}")
            logger.info(f"  Router: {deployment_data_v3['router']}")
            logger.info(f"  Position Manager: {deployment_data_v3['position_manager']}")
            logger.info(f"  Quoter: {deployment_data_v3['quoter']}")

            self._router = deployment_data_v3["router"]
            self._factory = deployment_data_v3["factory"]
            return True

        return False
