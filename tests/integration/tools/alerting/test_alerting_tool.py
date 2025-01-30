from alphaswarm.tools.alerting.alerting_tool import SendTradeAlert
from alphaswarm.tools.strategies.momentum.momentum_analysis_tool import StrategyAnalysis, MomentumItem


def test_send_trade_alert():
    tool = SendTradeAlert()

    # Create a mock StrategyAnalysis object
    momentum_items = [
        MomentumItem(symbol="WETH", rule="price_momentum", value=4.0),
        MomentumItem(symbol="VIRTUAL", rule="price_momentum", value=2.1),
    ]
    analysis = StrategyAnalysis(momentum_items=momentum_items, analysis="Test analysis for WETH and VIRTUAL tokens")

    # Test sending alert
    tool.forward(analysis)
    # The tool prints to console, so we mainly verify it doesn't raise exceptions
    # and accepts the StrategyAnalysis object correctly
