from alphaswarm.services.chains.evm import ZERO_CHECKSUM_ADDRESS
from alphaswarm.services.exchanges.uniswap.uniswap_client_v3 import ExactInputSingleParams


def test_v3_router_contract() -> None:
    params = ExactInputSingleParams(
        token_in=ZERO_CHECKSUM_ADDRESS,
        token_out=ZERO_CHECKSUM_ADDRESS,
        fee=0,
        recipient=ZERO_CHECKSUM_ADDRESS,
        deadline=0,
        amount_in=0,
        amount_out_minimum=0,
        sqrt_price_limit_x96=0,
    )

    result = params.to_dict()
    assert result["tokenOut"] == ZERO_CHECKSUM_ADDRESS
