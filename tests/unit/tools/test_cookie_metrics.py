import pytest
from unittest.mock import Mock, patch

from alphaswarm.services.cookiefun.cookiefun_client import (
    CookieFunClient,
    AgentMetrics,
    Interval
)
from alphaswarm.tools.cookie.cookie_metrics import (
    CookieMetricsByTwitter,
    CookieMetricsByContract
)

@pytest.fixture
def mock_response():
    return {
        "ok": {
            "agentName": "TestAgent",
            "contracts": [
                {
                    "chain": 8453,
                    "contractAddress": "0x123"
                }
            ],
            "twitterUsernames": ["test_agent"],
            "mindshare": 1.5,
            "mindshareDeltaPercent": 10.0,
            "marketCap": 1000000.0,
            "marketCapDeltaPercent": 5.0,
            "price": 1.0,
            "priceDeltaPercent": 2.0,
            "liquidity": 500000.0,
            "volume24Hours": 100000.0,
            "volume24HoursDeltaPercent": 3.0,
            "holdersCount": 1000,
            "holdersCountDeltaPercent": 4.0,
            "averageImpressionsCount": 5000.0,
            "averageImpressionsCountDeltaPercent": 6.0,
            "averageEngagementsCount": 100.0,
            "averageEngagementsCountDeltaPercent": 7.0,
            "followersCount": 5000,
            "smartFollowersCount": 200,
            "topTweets": [
                {
                    "tweet_url": "https://x.com/test",
                    "tweet_author_profile_image_url": "https://image.url",
                    "tweet_author_display_name": "Test User",
                    "smart_engagement_points": 10,
                    "impressions_count": 1000
                }
            ]
        },
        "success": True,
        "error": None
    }

@pytest.fixture
def mock_client(mock_response):
    with patch.dict('os.environ', {'COOKIE_FUN_API_KEY': 'test_key'}):
        client = CookieFunClient()
        client.get_agent_by_twitter = Mock(return_value=client._parse_agent_response(mock_response))
        client.get_agent_by_contract = Mock(return_value=client._parse_agent_response(mock_response))
        return client

def test_cookie_metrics_by_twitter(mock_client):
    tool = CookieMetricsByTwitter(client=mock_client)
    result = tool.forward("test_agent", Interval.SEVEN_DAYS)
    
    assert isinstance(result, AgentMetrics)
    assert result.agent_name == "TestAgent"
    assert result.mindshare == 1.5
    assert len(result.contracts) == 1
    assert result.contracts[0].chain == 8453

def test_cookie_metrics_by_contract(mock_client):
    tool = CookieMetricsByContract(client=mock_client)
    result = tool.forward("0x123", Interval.THREE_DAYS)
    
    assert isinstance(result, AgentMetrics)
    assert result.agent_name == "TestAgent"
    assert result.price == 1.0
    assert result.market_cap == 1000000.0

def test_invalid_api_key():
    with patch.dict('os.environ', clear=True):
        with pytest.raises(ValueError, match="COOKIE_FUN_API_KEY environment variable not set"):
            CookieFunClient()

@pytest.mark.parametrize("interval", [
    Interval.THREE_DAYS,
    Interval.SEVEN_DAYS
])
def test_valid_intervals(mock_client, interval):
    tool = CookieMetricsByTwitter(client=mock_client)
    result = tool.forward("test_agent", interval)
    assert isinstance(result, AgentMetrics) 