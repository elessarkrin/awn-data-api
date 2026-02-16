import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

logger = logging.getLogger(__name__)
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.converter import FIELD_DESCRIPTIONS, MAX_FIELDS, MIN_FIELDS, SKIP_FIELDS
from app.database import DailyReading, get_session
from app.schemas import (
    DailyReadingResponse,
    FieldDescription,
    LatestReadingResponse,
    PaginatedDailyResponse,
)
from app.statistics import get_reading_statistics

router = APIRouter(prefix="/history", tags=["history"])


@router.get(
    "/fields",
    response_model=dict[str, FieldDescription],
    summary="List available sensor fields",
    description="Returns metadata for each sensor field that appears in reading responses. "
    "Each entry maps a field name to its human-readable description and unit of measurement. "
    "Use this to understand the `data` object returned by the history and latest endpoints.",
    responses={
        200: {
            "description": "Field descriptions keyed by field name",
            "content": {
                "application/json": {
                    "example": {
                        "temp_c": {"description": "Outdoor Temperature", "unit": "°C"},
                        "vpd_kpa": {
                            "description": "Vapor Pressure Deficit (derived from temp_c and humidity)",
                            "unit": "kPa",
                        },
                        "beaufort_scale": {
                            "description": "Wind force category from wind_speed_kmh (0-12)",
                            "unit": "scale",
                        },
                        "barom_rel_mmhg": {"description": "Relative Pressure", "unit": "mmHg"},
                        "humidity": {"description": "Outdoor Humidity", "unit": "%"},
                    }
                }
            },
        }
    },
)
async def get_field_descriptions():
    """Return metadata describing each field that may appear in a reading response."""
    return FIELD_DESCRIPTIONS


@router.get(
    "",
    response_model=PaginatedDailyResponse,
    summary="Get historical readings",
    description="Returns a paginated list of weather station readings ordered by timestamp "
    "(most recent first). Readings are recorded at the station's 5-minute reporting cadence "
    "and retained for 365 days. On startup, up to one year of history is backfilled. "
    "All sensor values are converted to metric units at ingestion time. "
    "Use the `start` and `end` parameters to query a specific time window.",
)
async def get_daily_readings(
    session: AsyncSession = Depends(get_session),
    mac_address: str = Query(
        default=None,
        description="Weather station MAC address. Defaults to the configured station.",
        examples=["AA:BB:CC:DD:EE:FF"],
    ),
    start: datetime | None = Query(
        default=None,
        description="Include only readings at or after this UTC datetime.",
        examples=["2026-02-01T00:00:00Z"],
    ),
    end: datetime | None = Query(
        default=None,
        description="Include only readings at or before this UTC datetime.",
        examples=["2026-02-04T23:59:59Z"],
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=10000,
        description="Maximum number of readings to return per page.",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of readings to skip for pagination.",
    ),
):
    """Get paginated historical readings with optional date range filtering."""
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


@router.get(
    "/latest",
    response_model=LatestReadingResponse | None,
    summary="Get the latest reading",
    description="Returns the single most recent weather station reading, "
    "plus aggregate station statistics. "
    "Returns null if no readings have been collected yet.",
    responses={
        200: {
            "description": "The most recent reading with statistics, or null if none exist",
        }
    },
)
async def get_latest_reading(
    session: AsyncSession = Depends(get_session),
    mac_address: str = Query(
        default=None,
        description="Weather station MAC address. Defaults to the configured station.",
        examples=["AA:BB:CC:DD:EE:FF"],
    ),
):
    """Get the most recent reading."""
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
    statistics = await get_reading_statistics(mac, session=session)
    return LatestReadingResponse(
        reading=DailyReadingResponse.model_validate(reading),
        statistics=statistics,
    )


def _aggregate_daily(readings: list) -> list[DailyReadingResponse]:
    """Group readings by date and emit 3 entries per day: min, avg, max."""
    by_day: dict[str, list] = defaultdict(list)
    for r in readings:
        day_key = r.timestamp.strftime("%Y-%m-%d")
        by_day[day_key].append(r)

    results = []
    for day_key in sorted(by_day.keys(), reverse=True):
        day_entries = by_day[day_key]
        day_data = [r.data for r in day_entries]
        representative = day_entries[0]

        # Collect numeric values per field
        all_keys: set[str] = set()
        for d in day_data:
            all_keys.update(d.keys())

        field_values: dict[str, list[float]] = {}
        for key in all_keys:
            if key in SKIP_FIELDS:
                continue
            values = [
                d[key] for d in day_data
                if key in d and isinstance(d[key], (int, float))
            ]
            if values:
                field_values[key] = values

        base_ts = datetime.strptime(day_key, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        # min at 00:00, avg at 12:00, max at 23:59
        timestamps = [
            base_ts,
            base_ts.replace(hour=12),
            base_ts.replace(hour=23, minute=59, second=59),
        ]

        for ts, agg_fn in zip(
            timestamps,
            [min, lambda vs: sum(vs) / len(vs), max],
        ):
            entry: dict = {}
            for key, values in field_values.items():
                entry[key] = round(agg_fn(values), 2)
            entry["date"] = ts.isoformat()
            entry["date_utc"] = int(ts.timestamp() * 1000)
            entry["battout"] = 1

            results.append(DailyReadingResponse(
                id=representative.id,
                timestamp=ts,
                data=entry,
            ))

    return results


@router.get(
    "/range",
    response_model=PaginatedDailyResponse,
    summary="Get readings for a date range",
    description="Returns readings between `start` and `end` (inclusive). "
    "For ranges of 30 days or less, returns individual readings ordered by timestamp (most recent first). "
    "For ranges over 30 days, returns one aggregated summary per day "
    "(averages for most fields, max for peak/cumulative fields like gusts, rain, UV, solar).",
)
async def get_readings_by_range(
    start: datetime = Query(
        description="Start of the date range (inclusive, UTC).",
        examples=["2026-02-01T00:00:00Z"],
    ),
    session: AsyncSession = Depends(get_session),
    mac_address: str = Query(
        default=None,
        description="Weather station MAC address. Defaults to the configured station.",
        examples=["AA:BB:CC:DD:EE:FF"],
    ),
    end: datetime = Query(
        default=None,
        description="End of the date range (inclusive, UTC). Defaults to current time.",
        examples=["2026-02-09T23:59:59Z"],
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=10000,
        description="Maximum number of readings to return per page.",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of readings to skip for pagination.",
    ),
):
    """Get paginated readings within a date range."""
    mac = mac_address or settings.awn_mac_address
    effective_end = end or datetime.now(timezone.utc)
    range_days = (effective_end - start).total_seconds() / 86400

    base_filter = [
        DailyReading.mac_address == mac,
        DailyReading.timestamp >= start,
        DailyReading.timestamp <= effective_end,
    ]

    if range_days > 30:
        # Aggregated daily summaries
        logger.info("Range %.0f days > 30: returning daily aggregated summaries", range_days)
        query = select(DailyReading).where(*base_filter).order_by(DailyReading.timestamp.desc())
        result = await session.execute(query)
        all_readings = result.scalars().all()
        summaries = _aggregate_daily(all_readings)
        return PaginatedDailyResponse(
            items=summaries,
            total=len(summaries),
            limit=len(summaries),
            offset=0,
        )

    count_query = select(func.count(DailyReading.id)).where(*base_filter)
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    query = (
        select(DailyReading)
        .where(*base_filter)
        .order_by(DailyReading.timestamp.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(query)
    readings = result.scalars().all()

    return PaginatedDailyResponse(
        items=[DailyReadingResponse.model_validate(r) for r in readings],
        total=total,
        limit=limit,
        offset=offset,
    )
