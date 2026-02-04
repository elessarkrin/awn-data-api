"""Background service that collects data from Ambient Weather API,
stores daily readings, and broadcasts to SSE subscribers."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import delete, select

from app.broadcast import broadcaster
from app.config import settings
from app.converter import convert_reading
from app.database import (
    DailyReading,
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


async def store_daily_reading(converted: dict, mac_address: str) -> None:
    """Store a converted reading in the daily_readings table."""
    async with async_session() as session:
        reading = DailyReading(
            timestamp=datetime.now(timezone.utc),
            mac_address=mac_address,
            data=converted,
        )
        session.add(reading)
        await session.commit()


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
                await store_daily_reading(converted, mac)

                # Purge old daily readings
                deleted = await purge_old_readings(mac)
                if deleted:
                    logger.info("Purged %d old daily readings", deleted)

                # Broadcast to SSE subscribers
                await broadcaster.publish(converted)

                logger.debug("Collected and stored reading")

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
