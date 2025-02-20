import pytest

from alphaswarm.services.cookiefun.cookiefun_client import CookieFunClient, Interval
from alphaswarm.tools.cookie.cookie_metrics import (
    GetCookieMetricsByTwitter,
    GetCookieMetricsByContract,
    GetCookieMetricsBySymbol,
    GetCookieMetricsPaged,
)


@pytest.mark.skip("Needs Cookie.fun API key")
def test_get_metrics_by_twitter(cookiefun_client: CookieFunClient) -> None:
    tool = GetCookieMetricsByTwitter(cookiefun_client)
    result = tool.forward(username="cookiedotfun", interval=Interval.SEVEN_DAYS)

    assert result.agent_name == "Cookie"
    assert result.price > 0
    assert result.market_cap > 0
    assert len(result.contracts) > 0
    assert len(result.twitter_usernames) > 0


@pytest.mark.skip("Needs Cookie.fun API key")
def test_get_metrics_by_contract(cookiefun_client: CookieFunClient) -> None:
    tool = GetCookieMetricsByContract(cookiefun_client)
    cookie_address = "0xc0041ef357b183448b235a8ea73ce4e4ec8c265f"  # Cookie token on Base
    result = tool.forward(address=cookie_address, chain="base-mainnet", interval=Interval.SEVEN_DAYS)

    assert result.agent_name == "Cookie"
    assert result.price > 0
    assert result.market_cap > 0
    assert any(c.contract_address == cookie_address for c in result.contracts)


@pytest.mark.skip("Needs Cookie.fun API key")
def test_get_metrics_by_symbol(cookiefun_client: CookieFunClient) -> None:
    tool = GetCookieMetricsBySymbol(cookiefun_client)
    result = tool.forward(symbol="COOKIE", interval=Interval.SEVEN_DAYS)

    assert result.agent_name == "Cookie"
    assert result.price > 0
    assert result.market_cap > 0
    assert len(result.contracts) > 0


@pytest.mark.skip("Needs Cookie.fun API key")
def test_get_metrics_paged(cookiefun_client: CookieFunClient) -> None:
    tool = GetCookieMetricsPaged(cookiefun_client)
    result = tool.forward(interval=Interval.SEVEN_DAYS, page=1, page_size=10)

    assert result.current_page == 1
    assert result.total_pages > 0
    assert result.total_count > 0
    assert len(result.data) == 10
    assert all(agent.price > 0 for agent in result.data)
