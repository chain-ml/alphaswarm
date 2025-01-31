from alphaswarm.tools.alerting.alerting_tool import SendTradeAlert
from alphaswarm.tools.strategy_analysis.generic.generic_analysis import StrategyAnalysis, AlertItem


def test_send_trade_alert():
    tool = SendTradeAlert()

    # Create a mock StrategyAnalysis object
    alert_items = [
        AlertItem(
            metadata={"symbol": "WETH", "chain": "ethereum"},
            rule_description="Price increased significantly",
            value=4.0,
            supporting_data={"time_period": "24h"},
        )
    ]

    analysis = StrategyAnalysis(summary="Test analysis for WETH token", alerts=alert_items)

    # Test sending alert
    tool.forward(analysis)
    # The tool prints to console, so we mainly verify it doesn't raise exceptions
    # and accepts the StrategyAnalysis object correctly
