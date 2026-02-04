from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import DailyReading, get_session
from app.schemas import DailyReadingResponse, PaginatedDailyResponse

router = APIRouter(prefix="/daily", tags=["daily"])


@router.get("", response_model=PaginatedDailyResponse)
async def get_daily_readings(
    session: AsyncSession = Depends(get_session),
    mac_address: str = Query(default=None, description="Filter by MAC address"),
    start: datetime | None = Query(default=None, description="Start datetime (UTC)"),
    end: datetime | None = Query(default=None, description="End datetime (UTC)"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """Get paginated daily readings with optional date range filtering."""
    mac = mac_address or settings.awn_mac_address

    # Build base query
    query = select(DailyReading).where(DailyReading.mac_address == mac)
    count_query = select(func.count(DailyReading.id)).where(DailyReading.mac_address == mac)

    if start:
        query = query.where(DailyReading.timestamp >= start)
        count_query = count_query.where(DailyReading.timestamp >= start)
    if end:
        query = query.where(DailyReading.timestamp <= end)
        count_query = count_query.where(DailyReading.timestamp <= end)

    # Get total count
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    # Get paginated results
    query = query.order_by(DailyReading.timestamp.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    readings = result.scalars().all()

    return PaginatedDailyResponse(
        items=[DailyReadingResponse.model_validate(r) for r in readings],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/latest", response_model=DailyReadingResponse | None)
async def get_latest_reading(
    session: AsyncSession = Depends(get_session),
    mac_address: str = Query(default=None, description="Filter by MAC address"),
):
    """Get the most recent daily reading."""
    mac = mac_address or settings.awn_mac_address
    result = await session.execute(
        select(DailyReading)
        .where(DailyReading.mac_address == mac)
        .order_by(DailyReading.timestamp.desc())
        .limit(1)
    )
    reading = result.scalar_one_or_none()
    if reading is None:
        return None
    return DailyReadingResponse.model_validate(reading)
