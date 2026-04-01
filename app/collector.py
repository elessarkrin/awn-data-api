"""Background service that collects data from Ambient Weather API,
stores daily readings, and broadcasts to SSE subscribers."""

import asyncio
import logging
import random
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.broadcast import broadcaster
from app.config import settings
from app.converter import add_derived_metrics, convert_reading, strip_sensitive_fields
from app.database import (
    DailyReading,
    async_session,
)
from app.statistics import get_reading_statistics, invalidate_statistics_cache

logger = logging.getLogger(__name__)

AWN_API_BASE = "https://rt.ambientweather.net/v1"


def generate_mock_reading() -> dict:
    """Generate realistic mock weather data for testing without AWN credentials."""
    base_temp = 15 + random.uniform(-5, 10)  # 10-25°C

    return {
        "temp_c": round(base_temp, 2),
        "feels_like_c": round(base_temp + random.uniform(-3, 3), 2),
        "dew_point_c": round(base_temp - random.uniform(5, 15), 2),
        "humidity": random.randint(40, 85),
        "wind_speed_kmh": round(random.uniform(0, 20), 2),
        "wind_gust_kmh": round(random.uniform(5, 35), 2),
        "max_daily_gust_kmh": round(random.uniform(20, 45), 2),
        "wind_dir": random.randint(0, 360),
        "wind_gust_dir": random.randint(0, 360),
        "barom_rel_mmhg": round(750 + random.uniform(-10, 10), 2),
        "barom_abs_mmhg": round(760 + random.uniform(-10, 10), 2),
        "hourly_rain_mm": round(random.uniform(0, 5), 2),
        "daily_rain_mm": round(random.uniform(0, 20), 2),
        "weekly_rain_mm": round(random.uniform(0, 50), 2),
        "monthly_rain_mm": round(random.uniform(0, 100), 2),
        "yearly_rain_mm": round(random.uniform(100, 500), 2),
        "event_rain_mm": round(random.uniform(0, 30), 2),
        "total_rain_mm": round(random.uniform(500, 2000), 2),
        "solar_radiation": round(random.uniform(0, 1000), 2),
        "uv": round(random.uniform(0, 11), 1),
        "date": datetime.now(timezone.utc).isoformat(),
        "date_utc": int(datetime.now(timezone.utc).timestamp() * 1000),
    }


async def fetch_readings_page(
    end_date: str | None = None, limit: int = 1
) -> list[dict]:
    """Fetch up to `limit` readings from the AWN REST API.

    Args:
        end_date: Optional ISO 8601 date upper bound for pagination.
        limit: Number of records to request (max 288).

    Returns:
        List of raw AWN reading dicts, newest first.
    """
    url = f"{AWN_API_BASE}/devices/{settings.awn_mac_address}"
    params = {
        "apiKey": settings.awn_api_key,
        "applicationKey": settings.awn_application_key,
        "limit": limit,
    }
    if end_date is not None:
        params["endDate"] = end_date
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if data and isinstance(data, list):
            return data
    return []


async def upsert_readings(readings: list[dict], mac_address: str) -> int:
    """Batch upsert converted readings using SQLite ON CONFLICT DO UPDATE.

    Each reading must contain a `date_utc` field (epoch ms) used as the timestamp.
    Returns the number of rows upserted.
    """
    if not readings:
        return 0

    rows = []
    for reading in readings:
        date_utc_ms = reading.get("date_utc")
        if date_utc_ms is None:
            continue
        ts = datetime.fromtimestamp(date_utc_ms / 1000, tz=timezone.utc)
        rows.append({
            "timestamp": ts,
            "mac_address": mac_address,
            "data": reading,
        })

    if not rows:
        return 0

    async with async_session() as session:
        stmt = sqlite_insert(DailyReading).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["timestamp", "mac_address"],
            set_={"data": stmt.excluded.data},
        )
        await session.execute(stmt)
        await session.commit()
    await invalidate_statistics_cache(mac_address)
    return len(rows)


async def get_reading_boundary(mac_address: str, newest: bool = False) -> datetime | None:
    """Return the oldest (or newest) reading timestamp for a MAC, or None if empty."""
    agg = func.max if newest else func.min
    async with async_session() as session:
        result = await session.execute(
            select(agg(DailyReading.timestamp)).where(
                DailyReading.mac_address == mac_address
            )
        )
        ts = result.scalar_one_or_none()
        if ts is None:
            return None
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts


async def _paginate_backward(
    mac_address: str,
    *,
    start_end_date: str | None,
    stop_at: datetime,
    label: str,
) -> int:
    """Page backward through the AWN API, upsert readings, stop at `stop_at` datetime.

    Returns total number of readings upserted.
    """
    batch_size = settings.backfill_batch_size
    delay = settings.backfill_request_delay
    total_upserted = 0
    batch_num = 0
    end_date = start_end_date

    while True:
        batch_num += 1
        if end_date is not None:
            logger.info("%s batch %d: fetching from %s", label, batch_num, end_date)
        else:
            logger.info("%s batch %d: fetching most recent data", label, batch_num)
        try:
            raw_readings = await fetch_readings_page(
                end_date=end_date, limit=batch_size
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                logger.warning("%s rate limited, waiting 5s before retry", label)
                await asyncio.sleep(5)
                continue
            logger.error("%s HTTP error: %s", label, exc)
            break
        except httpx.RequestError as exc:
            logger.error("%s request error: %s", label, exc)
            break

        if not raw_readings:
            logger.info("%s complete: no more data from API", label)
            break

        converted = [convert_reading(r) for r in raw_readings]
        upserted = await upsert_readings(converted, mac_address)
        total_upserted += upserted

        oldest_date = min(
            (r.get("date", "") for r in raw_readings),
            default="",
        )

        logger.info(
            "%s batch %d: fetched=%d, upserted=%d, total=%d, oldest=%s",
            label, batch_num, len(raw_readings), upserted, total_upserted,
            oldest_date or "N/A",
        )

        if oldest_date:
            oldest_dt = datetime.fromisoformat(oldest_date)
            if oldest_dt.tzinfo is None:
                oldest_dt = oldest_dt.replace(tzinfo=timezone.utc)
            if oldest_dt <= stop_at:
                logger.info("%s reached target date", label)
                break

        next_end_date = oldest_date if oldest_date else None
        if next_end_date == end_date:
            logger.info("%s complete: end date unchanged (%s)", label, end_date)
            break
        end_date = next_end_date

        await asyncio.sleep(delay)

    return total_upserted


async def backfill_history(mac_address: str) -> int:
    """Fill gaps in the database by paginating backward through the AWN API.

    Empty DB: fetches from now backward up to backfill_days.
    Existing data: two passes —
      1. From now backward until reaching the newest existing reading (fill recent gap).
      2. From the oldest existing reading backward until the cutoff (fill historic gap).

    Returns total number of readings upserted.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.backfill_days)

    oldest_existing = await get_reading_boundary(mac_address, newest=False)
    newest_existing = await get_reading_boundary(mac_address, newest=True)

    total = 0

    if oldest_existing is None:
        # Empty DB — full backfill from now
        logger.info(
            "Starting initial backfill: cutoff=%s",
            cutoff.strftime("%Y-%m-%d %H:%M:%S"),
        )
        total += await _paginate_backward(
            mac_address,
            start_end_date=None,
            stop_at=cutoff,
            label="Backfill",
        )
    else:
        # Pass 1: fill gap from now to newest existing reading
        logger.info(
            "Filling recent gap: now -> %s",
            newest_existing.strftime("%Y-%m-%d %H:%M:%S"),
        )
        total += await _paginate_backward(
            mac_address,
            start_end_date=None,
            stop_at=newest_existing,
            label="Recent fill",
        )

        # Pass 2: fill gap from oldest existing reading to cutoff
        if oldest_existing > cutoff:
            logger.info(
                "Filling historic gap: %s -> %s",
                oldest_existing.strftime("%Y-%m-%d %H:%M:%S"),
                cutoff.strftime("%Y-%m-%d %H:%M:%S"),
            )
            total += await _paginate_backward(
                mac_address,
                start_end_date=oldest_existing.isoformat(),
                stop_at=cutoff,
                label="Historic fill",
            )
        else:
            logger.info("Historic data already reaches cutoff")

    logger.info("Backfill finished: total upserted=%d", total)
    return total


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


def _seconds_until_next_tick(tick_minutes: int = 5) -> float:
    """Return seconds until the next clock-aligned tick (e.g. :00, :05, :10, ...)."""
    now = datetime.now(timezone.utc)
    current_seconds = now.minute * 60 + now.second + now.microsecond / 1_000_000
    tick_seconds = tick_minutes * 60
    elapsed = current_seconds % tick_seconds
    return tick_seconds - elapsed


async def collection_loop() -> None:
    """Main collection loop that runs as a background task.

    Fetches immediately on startup, then on clock-aligned 5-minute ticks.
    Uses real AWN API if credentials are configured, otherwise generates mock data.
    """
    mac = settings.awn_mac_address
    use_mock = not (settings.awn_api_key and settings.awn_application_key)
    tick_minutes = settings.collection_interval_seconds // 60 or 5

    logger.info(
        "Starting collector: mac=%s, tick=%dm, retention=%dd, mode=%s",
        mac,
        tick_minutes,
        settings.daily_retention_days,
        "mock" if use_mock else "real",
    )

    first_run = True
    while True:
        # On first run fetch immediately; afterwards sleep until next clock tick
        if not first_run:
            wait = _seconds_until_next_tick(tick_minutes)
            logger.info("Next collection in %.0fs", wait)
            try:
                await asyncio.sleep(wait)
            except asyncio.CancelledError:
                logger.info("Collection loop cancelled during sleep, shutting down")
                raise
        first_run = False

        try:
            if use_mock:
                converted = add_derived_metrics(generate_mock_reading())
            else:
                raw_list = await fetch_readings_page(limit=1)
                if not raw_list:
                    logger.warning("No data returned from AWN API")
                    continue
                converted = convert_reading(raw_list[0])

            converted = strip_sensitive_fields(converted)
            await upsert_readings([converted], mac)

            # Purge old daily readings
            deleted = await purge_old_readings(mac)
            if deleted:
                logger.info("Purged %d old daily readings", deleted)

            # Broadcast to SSE subscribers
            statistics = await get_reading_statistics(mac)
            await broadcaster.publish({
                "reading": converted,
                "statistics": statistics.model_dump(mode="json"),
            })
            logger.info(
                "Published reading: subscribers=%d, temp=%.2f°C",
                broadcaster.subscriber_count,
                converted.get("temp_c", 0),
            )

        except asyncio.CancelledError:
            logger.info("Collection loop cancelled, shutting down")
            raise
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
