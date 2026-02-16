import logging
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, HTTPException

from app.config import settings
from app.schemas import AstronomyResponse, TwilightPeriod

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/astronomy", tags=["astronomy"])

_cache: AstronomyResponse | None = None
_cache_bucket_start: datetime | None = None


def _current_cache_bucket_start() -> datetime:
    now = datetime.now(UTC)
    return now.replace(minute=(now.minute // 5) * 5, second=0, microsecond=0)


async def _fetch_astronomy() -> AstronomyResponse:
    url = "https://api.ipgeolocation.io/v2/astronomy"
    params = {
        "apiKey": settings.astronomy_api_key,
        "lat": settings.lat,
        "long": settings.lon,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=10)
        resp.raise_for_status()
        body = resp.json()

    d = body["astronomy"]
    morning = d.get("morning")
    evening = d.get("evening")

    return AstronomyResponse(
        current_time=d.get("current_time"),
        date=d.get("date"),
        sunrise=d.get("sunrise"),
        sunset=d.get("sunset"),
        solar_noon=d.get("solar_noon"),
        mid_night=d.get("mid_night"),
        day_length=d.get("day_length"),
        sun_altitude=d.get("sun_altitude"),
        sun_azimuth=d.get("sun_azimuth"),
        sun_distance=d.get("sun_distance"),
        sun_status=d.get("sun_status"),
        moonrise=d.get("moonrise"),
        moonset=d.get("moonset"),
        moon_altitude=d.get("moon_altitude"),
        moon_azimuth=d.get("moon_azimuth"),
        moon_distance=d.get("moon_distance"),
        moon_parallactic_angle=d.get("moon_parallactic_angle"),
        moon_phase=d.get("moon_phase"),
        moon_illumination_percentage=d.get("moon_illumination_percentage"),
        moon_angle=d.get("moon_angle"),
        moon_status=d.get("moon_status"),
        night_begin=d.get("night_begin"),
        night_end=d.get("night_end"),
        morning=TwilightPeriod(**morning) if morning else None,
        evening=TwilightPeriod(**evening) if evening else None,
    )


async def _get_astronomy_cached() -> AstronomyResponse:
    global _cache, _cache_bucket_start
    bucket_start = _current_cache_bucket_start()
    if _cache is not None and _cache_bucket_start == bucket_start:
        return _cache

    logger.info(
        "Astronomy cache miss - fetching fresh data for bucket %s",
        bucket_start.isoformat(),
    )
    try:
        _cache = await _fetch_astronomy()
        _cache_bucket_start = bucket_start
        return _cache
    except (httpx.HTTPStatusError, httpx.RequestError):
        if _cache is not None:
            logger.warning(
                "Astronomy fetch failed for bucket %s - serving stale cache from bucket %s",
                bucket_start.isoformat(),
                _cache_bucket_start.isoformat() if _cache_bucket_start else "unknown",
            )
            return _cache
        raise


@router.get(
    "",
    response_model=AstronomyResponse,
    summary="Get astronomy data",
    description="Returns sun and moon data for the configured location. "
    "Data is cached per 5-minute UTC clock bucket (:00, :05, :10, ...). "
    "If an upstream fetch fails, the most recent cached value is returned when available.",
)
async def get_astronomy():
    if not settings.astronomy_api_key:
        raise HTTPException(status_code=503, detail="Astronomy API key not configured")
    try:
        return await _get_astronomy_cached()
    except httpx.HTTPStatusError as exc:
        logger.error("Astronomy API error: %s", exc)
        raise HTTPException(status_code=502, detail="Upstream astronomy API error")
    except httpx.RequestError as exc:
        logger.error("Astronomy API request failed: %s", exc)
        raise HTTPException(status_code=502, detail="Could not reach astronomy API")
