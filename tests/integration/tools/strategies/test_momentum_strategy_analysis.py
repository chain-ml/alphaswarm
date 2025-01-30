from alphaswarm.tools.strategies.momentum.momentum_analysis_tool import PriceMomentumStrategyAnalysisTool


def test_get_token_price_tool():
    tool = PriceMomentumStrategyAnalysisTool()
    result = tool.forward(percent_price_change_24_hour="WETH: +4%, VIRTUAL: +2.1%, AIXBT: +1.5%")
    assert result is not None
    # assert that the momentum items are correct
    assert result.momentum_items[0].symbol == "WETH"
    # assert result.momentum_items[0].rule == "price"
    assert result.momentum_items[0].value == 4.0
    assert result.momentum_items[1].symbol == "VIRTUAL"
    # assert result.momentum_items[1].rule == "price"
    assert result.momentum_items[1].value == 2.1
    # assert that the analysis is not empty
    assert result.analysis is not None
