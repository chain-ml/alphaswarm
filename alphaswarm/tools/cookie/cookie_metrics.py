import logging
from typing import Optional

from alphaswarm.services.cookiefun.cookiefun_client import AgentMetrics, CookieFunClient, Interval, PagedAgentsResponse
from smolagents import Tool

# Set up logging
logger = logging.getLogger(__name__)


class CookieMetricsByTwitter(Tool):
    name = "CookieMetricsByTwitter"
    description = "Retrieve AI agent metrics such as mindshare, market cap, price, liquidity, volume, holders, average impressions, average engagements, followers, and top tweets by Twitter username from Cookie.fun"
    inputs = {
        "username": {
            "type": "string",
            "description": "Twitter username of the agent",
        },
        "interval": {
            "type": "string",
            "description": "Time interval for metrics (_3Days or _7Days)",
            "enum": ["_3Days", "_7Days"],
        },
    }
    output_type = "object"

    def __init__(self, client: Optional[CookieFunClient] = None):
        super().__init__()
        self.client = client or CookieFunClient()

    def forward(self, username: str, interval: str) -> AgentMetrics:
        return self.client.get_agent_metrics_by_twitter(username, Interval(interval))


class CookieMetricsByContract(Tool):
    name = "CookieMetricsByContract"
    description = "Retrieve AI agent metrics such as mindshare, market cap, price, liquidity, volume, holders, average impressions, average engagements, followers, and top tweets by contract address or token symbol from Cookie.fun"
    inputs = {
        "address_or_symbol": {
            "type": "string",
            "description": "Contract address of the agent token or token symbol (e.g. 'COOKIE' or '0xc0041ef357b183448b235a8ea73ce4e4ec8c265f'). For addresses, chain must be specified.",
        },
        "chain": {
            "type": "string",
            "description": "Chain to look up token on (required only when using contract address)",
            "nullable": True,
        },
        "interval": {
            "type": "string",
            "description": "Time interval for metrics (_3Days or _7Days)",
            "enum": ["_3Days", "_7Days"],
        },
    }
    output_type = "object"

    def __init__(self, client: Optional[CookieFunClient] = None):
        super().__init__()
        self.client = client or CookieFunClient()

    def forward(self, address_or_symbol: str, interval: str, chain: Optional[str] = None) -> AgentMetrics:
        return self.client.get_agent_metrics_by_contract(address_or_symbol, Interval(interval), chain)


class CookieMetricsPaged(Tool):
    name = "CookieMetricsPaged"
    description = "Retrieve paged list of AI agents ordered by mindshare from Cookie.fun. Important for getting a list of trending AI agents. page_size is the number of agents per page. If asked for example for Top 10 agents, page_size should be 10."
    inputs = {
        "interval": {
            "type": "string",
            "description": "Time interval for metrics (_3Days or _7Days)",
            "enum": ["_3Days", "_7Days"],
        },
        "page": {
            "type": "integer",
            "description": "Page number (starts at 1)",
            "minimum": 1,
        },
        "page_size": {
            "type": "integer",
            "description": "Number of agents per page",
            "minimum": 1,
            "maximum": 25,
        },
    }
    output_type = "object"

    def __init__(self, client: Optional[CookieFunClient] = None):
        super().__init__()
        self.client = client or CookieFunClient()

    def forward(self, interval: str, page: int, page_size: int) -> PagedAgentsResponse:
        return self.client.get_agents_paged(Interval(interval), page, page_size)
