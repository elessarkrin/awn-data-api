from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import MonthlyAggregate, get_session
from app.schemas import AggregateMetric, MonthlyAggregateResponse

router = APIRouter(prefix="/monthly", tags=["monthly"])


@router.get("", response_model=list[MonthlyAggregateResponse])
async def get_monthly_aggregates(
    session: AsyncSession = Depends(get_session),
    mac_address: str = Query(default=None, description="Filter by MAC address"),
    year: int | None = Query(default=None, description="Filter by year"),
    month: int | None = Query(default=None, ge=1, le=12, description="Filter by month (1-12)"),
):
    """Get monthly aggregated metrics (min, max, avg for each numeric field)."""
    mac = mac_address or settings.awn_mac_address

    query = select(MonthlyAggregate).where(MonthlyAggregate.mac_address == mac)

    if year is not None:
        query = query.where(MonthlyAggregate.year == year)
    else:
        # Default to current year
        query = query.where(MonthlyAggregate.year == datetime.now(timezone.utc).year)

    if month is not None:
        query = query.where(MonthlyAggregate.month == month)

    query = query.order_by(MonthlyAggregate.year, MonthlyAggregate.month)

    result = await session.execute(query)
    rows = result.scalars().all()

    # Group by (year, month)
    grouped: dict[tuple[int, int], list[AggregateMetric]] = {}
    for row in rows:
        key = (row.year, row.month)
        grouped.setdefault(key, []).append(
            AggregateMetric(
                metric_name=row.metric_name,
                min_value=row.min_value,
                max_value=row.max_value,
                avg_value=row.avg_value,
                count=row.count,
            )
        )

    return [
        MonthlyAggregateResponse(
            mac_address=mac,
            year=year_val,
            month=month_val,
            metrics=metrics,
        )
        for (year_val, month_val), metrics in grouped.items()
    ]
