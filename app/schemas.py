from datetime import datetime

from pydantic import BaseModel


class DailyReadingResponse(BaseModel):
    id: int
    timestamp: datetime
    mac_address: str
    data: dict

    model_config = {"from_attributes": True}


class AggregateMetric(BaseModel):
    metric_name: str
    min_value: float
    max_value: float
    avg_value: float
    count: int

    model_config = {"from_attributes": True}


class MonthlyAggregateResponse(BaseModel):
    mac_address: str
    year: int
    month: int
    metrics: list[AggregateMetric]


class YearlyAggregateResponse(BaseModel):
    mac_address: str
    year: int
    metrics: list[AggregateMetric]


class PaginatedDailyResponse(BaseModel):
    items: list[DailyReadingResponse]
    total: int
    limit: int
    offset: int
