from typing import Optional

from alphaswarm.core.tool import AlphaSwarmTool
from alphaswarm.services.cookiefun.cookiefun_client import AgentMetrics, CookieFunClient, Interval, PagedAgentsResponse


class GetCookieMetricsByTwitter(AlphaSwarmTool):
    """
    Retrieve AI agent metrics such as mindshare, market cap, price, liquidity, volume, holders,
    average impressions, average engagements, followers, and top tweets by Twitter username from Cookie.fun
    """

    def __init__(self, client: Optional[CookieFunClient] = None):
        super().__init__()
        self.client = client or CookieFunClient()

    def forward(self, username: str, interval: str) -> AgentMetrics:
        """
        Args:
            username: Twitter username of the agent
            interval: Time interval for metrics (_3Days or _7Days)
        """
        return self.client.get_agent_metrics_by_twitter(username, Interval(interval))


class GetCookieMetricsByContract(AlphaSwarmTool):
    """
    Retrieve AI agent metrics such as mindshare, market cap, price, liquidity, volume, holders,
    average impressions, average engagements, followers, and top tweets by contract address from Cookie.fun
    """

    def __init__(self, client: Optional[CookieFunClient] = None):
        super().__init__()
        self.client = client or CookieFunClient()

    def forward(self, address: str, chain: str, interval: str) -> AgentMetrics:
        """
        Args:
            address: Contract address of the agent token (e.g. '0xc0041ef357b183448b235a8ea73ce4e4ec8c265f')
            chain: Chain where the contract is deployed (e.g. 'base-mainnet')
            interval: Time interval for metrics (_3Days or _7Days)
        """
        return self.client.get_agent_metrics_by_contract(address, Interval(interval), chain)


class GetCookieMetricsBySymbol(AlphaSwarmTool):
    """
    Retrieve AI agent metrics such as mindshare, market cap, price, liquidity, volume, holders,
    average impressions, average engagements, followers, and top tweets by token symbol from Cookie.fun
    """

    def __init__(self, client: Optional[CookieFunClient] = None):
        super().__init__()
        self.client = client or CookieFunClient()

    def forward(self, symbol: str, interval: str) -> AgentMetrics:
        """
        Args:
            symbol: Token symbol of the agent (e.g. 'COOKIE')
            interval: Time interval for metrics (_3Days or _7Days)
        """
        return self.client.get_agent_metrics_by_contract(symbol, Interval(interval))


class GetCookieMetricsPaged(AlphaSwarmTool):
    """
    Retrieve paged list of market data and statistics for `page_size` AI agent tokens ordered by mindshare from Cookie.fun.
    """

    def __init__(self, client: Optional[CookieFunClient] = None):
        super().__init__()
        self.client = client or CookieFunClient()

    def forward(self, interval: str, page: int, page_size: int) -> PagedAgentsResponse:
        """
        Args:
            interval: Time interval for metrics (_3Days or _7Days)
            page: Page number (starts at 1)
            page_size: Number of agents per page (from 1 to 25)
        """
        return self.client.get_agents_paged(Interval(interval), page, page_size)
