from datetime import datetime

from pydantic import BaseModel


class DailyReadingResponse(BaseModel):
    id: int
    timestamp: datetime
    mac_address: str
    data: dict

    model_config = {"from_attributes": True}



class FieldDescription(BaseModel):
    description: str
    unit: str


class PaginatedDailyResponse(BaseModel):
    items: list[DailyReadingResponse]
    total: int
    limit: int
    offset: int
