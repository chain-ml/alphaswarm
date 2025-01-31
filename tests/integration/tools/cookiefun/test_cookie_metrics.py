from alphaswarm.services.cookiefun.cookiefun_client import (
    CookieFunClient,
    Interval
)
from alphaswarm.tools.cookie.cookie_metrics import (
    CookieMetricsByTwitter,
    CookieMetricsByContract,
    CookieMetricsPaged
)


def test_get_metrics_by_twitter(cookiefun_client: CookieFunClient) -> None:
    tool = CookieMetricsByTwitter(cookiefun_client)
    result = tool.forward(username="cookiedotfun", interval=Interval.SEVEN_DAYS)

    assert result.agentName == "Cookie"
    assert result.price > 0
    assert result.marketCap > 0
    assert len(result.contracts) > 0
    assert len(result.twitterUsernames) > 0


def test_get_metrics_by_contract(cookiefun_client: CookieFunClient) -> None:
    tool = CookieMetricsByContract(cookiefun_client)
    cookie_address = "0xc0041ef357b183448b235a8ea73ce4e4ec8c265f"  # Cookie token on Base
    result = tool.forward(address=cookie_address, interval=Interval.SEVEN_DAYS)

    assert result.agentName == "Cookie"
    assert result.price > 0
    assert result.marketCap > 0
    assert any(c.contractAddress == cookie_address for c in result.contracts)


def test_get_metrics_paged(cookiefun_client: CookieFunClient) -> None:
    tool = CookieMetricsPaged(cookiefun_client)
    result = tool.forward(interval=Interval.SEVEN_DAYS, page=1, page_size=10)

    assert result.currentPage == 1
    assert result.totalPages > 0
    assert result.totalCount > 0
    assert len(result.data) == 10
    assert all(agent.price > 0 for agent in result.data) 