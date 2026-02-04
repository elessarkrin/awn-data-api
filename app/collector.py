"""Background service that collects data from Ambient Weather API,
stores daily readings, computes aggregates, and broadcasts to SSE subscribers."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import delete, func, select

from app.broadcast import broadcaster
from app.config import settings
from app.converter import convert_reading, get_numeric_fields
from app.database import (
    DailyReading,
    MonthlyAggregate,
    YearlyAggregate,
    async_session,
)

logger = logging.getLogger(__name__)

AWN_API_BASE = "https://rt.ambientweather.net/v1"


async def fetch_latest_reading() -> dict | None:
    """Fetch the most recent reading from the AWN REST API."""
    url = f"{AWN_API_BASE}/devices/{settings.awn_mac_address}"
    params = {
        "apiKey": settings.awn_api_key,
        "applicationKey": settings.awn_application_key,
        "limit": 1,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if data and isinstance(data, list) and len(data) > 0:
            return data[0]
    return None


async def store_daily_reading(converted: dict, mac_address: str) -> datetime:
    """Store a converted reading in the daily_readings table. Returns the timestamp."""
    now = datetime.now(timezone.utc)
    async with async_session() as session:
        reading = DailyReading(
            timestamp=now,
            mac_address=mac_address,
            data=converted,
        )
        session.add(reading)
        await session.commit()
    return now


async def purge_old_readings(mac_address: str) -> int:
    """Delete daily readings older than the retention period. Returns count deleted."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.daily_retention_days)
    async with async_session() as session:
        result = await session.execute(
            delete(DailyReading).where(
                DailyReading.mac_address == mac_address,
                DailyReading.timestamp < cutoff,
            )
        )
        await session.commit()
        return result.rowcount


async def update_monthly_aggregates(mac_address: str, ts: datetime) -> None:
    """Recompute monthly aggregates for the month of the given timestamp."""
    year = ts.year
    month = ts.month

    # Fetch all daily readings for this month
    async with async_session() as session:
        result = await session.execute(
            select(DailyReading.data).where(
                DailyReading.mac_address == mac_address,
                func.strftime("%Y", DailyReading.timestamp) == str(year),
                func.strftime("%m", DailyReading.timestamp) == f"{month:02d}",
            )
        )
        rows = result.scalars().all()

    if not rows:
        return

    # Collect all numeric values per metric
    metrics: dict[str, list[float]] = {}
    for data in rows:
        for key, value in get_numeric_fields(data).items():
            metrics.setdefault(key, []).append(value)

    # Upsert aggregates
    async with async_session() as session:
        for metric_name, values in metrics.items():
            existing = await session.execute(
                select(MonthlyAggregate).where(
                    MonthlyAggregate.mac_address == mac_address,
                    MonthlyAggregate.year == year,
                    MonthlyAggregate.month == month,
                    MonthlyAggregate.metric_name == metric_name,
                )
            )
            agg = existing.scalar_one_or_none()
            if agg:
                agg.min_value = min(values)
                agg.max_value = max(values)
                agg.avg_value = round(sum(values) / len(values), 2)
                agg.count = len(values)
            else:
                agg = MonthlyAggregate(
                    mac_address=mac_address,
                    year=year,
                    month=month,
                    metric_name=metric_name,
                    min_value=min(values),
                    max_value=max(values),
                    avg_value=round(sum(values) / len(values), 2),
                    count=len(values),
                )
                session.add(agg)
        await session.commit()


async def update_yearly_aggregates(mac_address: str, ts: datetime) -> None:
    """Recompute yearly aggregates for the year of the given timestamp."""
    year = ts.year

    async with async_session() as session:
        result = await session.execute(
            select(DailyReading.data).where(
                DailyReading.mac_address == mac_address,
                func.strftime("%Y", DailyReading.timestamp) == str(year),
            )
        )
        rows = result.scalars().all()

    if not rows:
        return

    metrics: dict[str, list[float]] = {}
    for data in rows:
        for key, value in get_numeric_fields(data).items():
            metrics.setdefault(key, []).append(value)

    async with async_session() as session:
        for metric_name, values in metrics.items():
            existing = await session.execute(
                select(YearlyAggregate).where(
                    YearlyAggregate.mac_address == mac_address,
                    YearlyAggregate.year == year,
                    YearlyAggregate.metric_name == metric_name,
                )
            )
            agg = existing.scalar_one_or_none()
            if agg:
                agg.min_value = min(values)
                agg.max_value = max(values)
                agg.avg_value = round(sum(values) / len(values), 2)
                agg.count = len(values)
            else:
                agg = YearlyAggregate(
                    mac_address=mac_address,
                    year=year,
                    metric_name=metric_name,
                    min_value=min(values),
                    max_value=max(values),
                    avg_value=round(sum(values) / len(values), 2),
                    count=len(values),
                )
                session.add(agg)
        await session.commit()


async def collection_loop() -> None:
    """Main collection loop that runs as a background task."""
    mac = settings.awn_mac_address
    interval = settings.collection_interval_seconds

    logger.info(
        "Starting collector: mac=%s, interval=%ds, retention=%dd",
        mac,
        interval,
        settings.daily_retention_days,
    )

    while True:
        try:
            raw = await fetch_latest_reading()
            if raw is None:
                logger.warning("No data returned from AWN API")
            else:
                converted = convert_reading(raw)
                ts = await store_daily_reading(converted, mac)

                # Update aggregates
                await update_monthly_aggregates(mac, ts)
                await update_yearly_aggregates(mac, ts)

                # Purge old daily readings
                deleted = await purge_old_readings(mac)
                if deleted:
                    logger.info("Purged %d old daily readings", deleted)

                # Broadcast to SSE subscribers
                await broadcaster.publish(converted)

                logger.debug("Collected and stored reading at %s", ts.isoformat())

        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                logger.warning("AWN API rate limited, backing off")
                await asyncio.sleep(5)
            else:
                logger.error("AWN API HTTP error: %s", exc)
        except httpx.RequestError as exc:
            logger.error("AWN API request error: %s", exc)
        except Exception:
            logger.exception("Unexpected error in collection loop")

        await asyncio.sleep(interval)
