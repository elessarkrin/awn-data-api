from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import YearlyAggregate, get_session
from app.schemas import AggregateMetric, YearlyAggregateResponse

router = APIRouter(prefix="/yearly", tags=["yearly"])


@router.get("", response_model=list[YearlyAggregateResponse])
async def get_yearly_aggregates(
    session: AsyncSession = Depends(get_session),
    mac_address: str = Query(default=None, description="Filter by MAC address"),
    year: int | None = Query(default=None, description="Filter by year"),
):
    """Get yearly aggregated metrics (min, max, avg for each numeric field)."""
    mac = mac_address or settings.awn_mac_address

    query = select(YearlyAggregate).where(YearlyAggregate.mac_address == mac)

    if year is not None:
        query = query.where(YearlyAggregate.year == year)
    else:
        query = query.where(YearlyAggregate.year == datetime.now(timezone.utc).year)

    query = query.order_by(YearlyAggregate.year)

    result = await session.execute(query)
    rows = result.scalars().all()

    # Group by year
    grouped: dict[int, list[AggregateMetric]] = {}
    for row in rows:
        grouped.setdefault(row.year, []).append(
            AggregateMetric(
                metric_name=row.metric_name,
                min_value=row.min_value,
                max_value=row.max_value,
                avg_value=row.avg_value,
                count=row.count,
            )
        )

    return [
        YearlyAggregateResponse(
            mac_address=mac,
            year=year_val,
            metrics=metrics,
        )
        for year_val, metrics in grouped.items()
    ]
