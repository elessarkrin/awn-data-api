from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from math import isfinite

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import DailyReading, async_session
from app.schemas import (
    DayExtreme,
    HumidityStatistics,
    MetricStatistics,
    RainStatistics,
    ReadingStatistics,
    SolarRadiationStatistics,
    TemperatureStatistics,
    WindStatistics,
)

_cache: dict[str, tuple[datetime, ReadingStatistics]] = {}
_cache_locks: dict[str, asyncio.Lock] = {}


@dataclass
class _DayMetrics:
    temps: list[float] = field(default_factory=list)
    rain_daily: list[float] = field(default_factory=list)
    rain_hourly: list[float] = field(default_factory=list)
    wind: list[float] = field(default_factory=list)
    gust: list[float] = field(default_factory=list)
    solar: list[float] = field(default_factory=list)
    humidity: list[float] = field(default_factory=list)


def _to_float(value) -> float | None:
    if isinstance(value, (int, float)):
        v = float(value)
        if isfinite(v):
            return v
    return None


def _round2(value: float) -> float:
    return round(value, 2)


def _summary(values: list[float]) -> MetricStatistics:
    if not values:
        return MetricStatistics()
    return MetricStatistics(
        min=_round2(min(values)),
        avg=_round2(sum(values) / len(values)),
        max=_round2(max(values)),
    )


def _pick_day_extreme(candidates: list[tuple[str, float]], maximize: bool) -> DayExtreme | None:
    if not candidates:
        return None
    ordered = sorted(candidates, key=lambda item: item[0])
    best = max(ordered, key=lambda item: item[1]) if maximize else min(ordered, key=lambda item: item[1])
    return DayExtreme(date=best[0], value=_round2(best[1]))


def _calculate_statistics(readings: list[DailyReading]) -> ReadingStatistics:
    if not readings:
        return ReadingStatistics(sample_count=0, range_start=None, range_end=None)

    temp_values: list[float] = []
    rain_values: list[float] = []
    wind_values: list[float] = []
    solar_values: list[float] = []
    humidity_values: list[float] = []
    days: dict[str, _DayMetrics] = defaultdict(_DayMetrics)

    earliest = min(readings, key=lambda r: r.timestamp).timestamp
    latest = max(readings, key=lambda r: r.timestamp).timestamp

    for reading in readings:
        data = reading.data or {}
        day_key = reading.timestamp.date().isoformat()
        day = days[day_key]

        temp = _to_float(data.get("temp_c"))
        if temp is not None:
            temp_values.append(temp)
            day.temps.append(temp)

        daily_rain = _to_float(data.get("daily_rain_mm"))
        hourly_rain = _to_float(data.get("hourly_rain_mm"))
        if daily_rain is not None:
            rain_values.append(daily_rain)
            day.rain_daily.append(daily_rain)
        elif hourly_rain is not None:
            rain_values.append(hourly_rain)
            day.rain_hourly.append(hourly_rain)

        wind = _to_float(data.get("wind_speed_kmh"))
        if wind is not None:
            wind_values.append(wind)
            day.wind.append(wind)

        gust = _to_float(data.get("wind_gust_kmh"))
        if gust is None:
            gust = _to_float(data.get("max_daily_gust_kmh"))
        if gust is not None:
            day.gust.append(gust)

        solar = _to_float(data.get("solar_radiation"))
        if solar is not None:
            solar_values.append(solar)
            day.solar.append(solar)

        humidity = _to_float(data.get("humidity"))
        if humidity is not None:
            humidity_values.append(humidity)
            day.humidity.append(humidity)

    hottest_candidates: list[tuple[str, float]] = []
    coldest_candidates: list[tuple[str, float]] = []
    wettest_candidates: list[tuple[str, float]] = []
    most_wind_candidates: list[tuple[str, float]] = []
    strongest_wind_candidates: list[tuple[str, float]] = []
    brightest_candidates: list[tuple[str, float]] = []
    darkest_candidates: list[tuple[str, float]] = []
    most_humid_candidates: list[tuple[str, float]] = []
    least_humid_candidates: list[tuple[str, float]] = []

    for day_key, day in days.items():
        if day.temps:
            hottest_candidates.append((day_key, max(day.temps)))
            coldest_candidates.append((day_key, min(day.temps)))

        if day.rain_daily:
            wettest_candidates.append((day_key, max(day.rain_daily)))
        elif day.rain_hourly:
            wettest_candidates.append((day_key, sum(day.rain_hourly)))

        if day.wind:
            most_wind_candidates.append((day_key, sum(day.wind) / len(day.wind)))
            strongest_wind_candidates.append((day_key, max(day.gust) if day.gust else max(day.wind)))

        if day.solar:
            avg_solar = sum(day.solar) / len(day.solar)
            brightest_candidates.append((day_key, avg_solar))
            darkest_candidates.append((day_key, avg_solar))

        if day.humidity:
            avg_humidity = sum(day.humidity) / len(day.humidity)
            most_humid_candidates.append((day_key, avg_humidity))
            least_humid_candidates.append((day_key, avg_humidity))

    temperature_summary = _summary(temp_values)
    rain_summary = _summary(rain_values)
    wind_summary = _summary(wind_values)
    solar_summary = _summary(solar_values)
    humidity_summary = _summary(humidity_values)

    return ReadingStatistics(
        sample_count=len(readings),
        range_start=earliest,
        range_end=latest,
        temperature=TemperatureStatistics(
            min=temperature_summary.min,
            avg=temperature_summary.avg,
            max=temperature_summary.max,
            hottest_day=_pick_day_extreme(hottest_candidates, maximize=True),
            coldest_day=_pick_day_extreme(coldest_candidates, maximize=False),
        ),
        rain=RainStatistics(
            min=rain_summary.min,
            avg=rain_summary.avg,
            max=rain_summary.max,
            wettest_day=_pick_day_extreme(wettest_candidates, maximize=True),
        ),
        wind=WindStatistics(
            min=wind_summary.min,
            avg=wind_summary.avg,
            max=wind_summary.max,
            day_with_most_wind=_pick_day_extreme(most_wind_candidates, maximize=True),
            strongest_wind=_pick_day_extreme(strongest_wind_candidates, maximize=True),
        ),
        solar_radiation=SolarRadiationStatistics(
            min=solar_summary.min,
            avg=solar_summary.avg,
            max=solar_summary.max,
            brightest_day=_pick_day_extreme(brightest_candidates, maximize=True),
            darkest_day=_pick_day_extreme(darkest_candidates, maximize=False),
        ),
        humidity=HumidityStatistics(
            min=humidity_summary.min,
            avg=humidity_summary.avg,
            max=humidity_summary.max,
            most_humid_day=_pick_day_extreme(most_humid_candidates, maximize=True),
            least_humid_day=_pick_day_extreme(least_humid_candidates, maximize=False),
        ),
    )


def _current_bucket_start() -> datetime:
    now = datetime.now(UTC)
    return now.replace(minute=(now.minute // 5) * 5, second=0, microsecond=0)


async def invalidate_statistics_cache(mac_address: str | None = None) -> None:
    """Invalidate cached station statistics for one MAC or all MACs."""
    if mac_address is None:
        _cache.clear()
        return
    _cache.pop(mac_address, None)


async def get_reading_statistics(
    mac_address: str,
    session: AsyncSession | None = None,
) -> ReadingStatistics:
    """Return aggregate weather statistics for a station MAC."""
    bucket_start = _current_bucket_start()
    cached = _cache.get(mac_address)
    if cached is not None and cached[0] == bucket_start:
        return cached[1]

    lock = _cache_locks.setdefault(mac_address, asyncio.Lock())
    async with lock:
        cached = _cache.get(mac_address)
        if cached is not None and cached[0] == bucket_start:
            return cached[1]

        if session is None:
            async with async_session() as owned_session:
                result = await owned_session.execute(
                    select(DailyReading)
                    .where(DailyReading.mac_address == mac_address)
                    .order_by(DailyReading.timestamp.asc())
                )
                readings = list(result.scalars().all())
        else:
            result = await session.execute(
                select(DailyReading)
                .where(DailyReading.mac_address == mac_address)
                .order_by(DailyReading.timestamp.asc())
            )
            readings = list(result.scalars().all())

        statistics = _calculate_statistics(readings)
        _cache[mac_address] = (bucket_start, statistics)
        return statistics
