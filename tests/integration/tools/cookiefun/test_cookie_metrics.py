from alphaswarm.services.cookiefun.cookiefun_client import CookieFunClient, Interval
from alphaswarm.tools.cookie.cookie_metrics import CookieMetricsByTwitter, CookieMetricsByContract, CookieMetricsPaged


def test_get_metrics_by_twitter(cookiefun_client: CookieFunClient) -> None:
    tool = CookieMetricsByTwitter(cookiefun_client)
    result = tool.forward(username="cookiedotfun", interval=Interval.SEVEN_DAYS)

    assert result.agent_name == "Cookie"
    assert result.price > 0
    assert result.market_cap > 0
    assert len(result.contracts) > 0
    assert len(result.twitter_usernames) > 0


def test_get_metrics_by_contract_address(cookiefun_client: CookieFunClient) -> None:
    tool = CookieMetricsByContract(cookiefun_client)
    cookie_address = "0xc0041ef357b183448b235a8ea73ce4e4ec8c265f"  # Cookie token on Base
    result = tool.forward(address_or_symbol=cookie_address, interval=Interval.SEVEN_DAYS)

    assert result.agent_name == "Cookie"
    assert result.price > 0
    assert result.market_cap > 0
    assert any(c.contract_address == cookie_address for c in result.contracts)


def test_get_metrics_by_contract_symbol(cookiefun_client: CookieFunClient) -> None:
    tool = CookieMetricsByContract(cookiefun_client)
    result = tool.forward(address_or_symbol="COOKIE", interval=Interval.SEVEN_DAYS)

    assert result.agent_name == "Cookie"
    assert result.price > 0
    assert result.market_cap > 0
    assert len(result.contracts) > 0


def test_get_metrics_paged(cookiefun_client: CookieFunClient) -> None:
    tool = CookieMetricsPaged(cookiefun_client)
    result = tool.forward(interval=Interval.SEVEN_DAYS, page=1, page_size=10)

    assert result.current_page == 1
    assert result.total_pages > 0
    assert result.total_count > 0
    assert len(result.data) == 10
    assert all(agent.price > 0 for agent in result.data)
