from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class Metric(str, Enum):
    PRICE = "price"


class MeasurementWindow(str, Enum):
    FIVE_MIN = "5min"
    ONE_HOUR = "1hr"
    ONE_DAY = "1d"


class MetricRule(BaseModel):
    metric: Metric = Field(..., description="Metric of interest")
    threshold_percentage: float = Field(..., description="Percentage change that triggers the rule", ge=-100.0)
    measurement_window: MeasurementWindow = Field(..., description="Measurement window for comparison")


class Strategy(BaseModel):
    name: str = Field(..., description="Name of the strategy")
    token: List[str] = Field(..., description="Ticker of tokens for which to apply rules", min_items=1)
    metric_rules: List[MetricRule] = Field(
        ..., description="List of conditions that must ALL be met to trigger the alert", min_items=1
    )

    class Config:
        use_enum_values = True
