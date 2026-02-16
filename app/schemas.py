from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.converter import strip_sensitive_fields


READING_DATA_EXAMPLE = {
    "temp_c": 19.11,
    "temp_in_c": 21.78,
    "feels_like_c": 19.11,
    "feels_like_in_c": 21.67,
    "dew_point_c": 15.18,
    "dew_point_in_c": 14.39,
    "humidity": 78,
    "vpd_kpa": 0.49,
    "humidity_in": 63,
    "wind_speed_kmh": 6.49,
    "beaufort_scale": 2,
    "wind_gust_kmh": 9.37,
    "max_daily_gust_kmh": 34.92,
    "wind_dir": 31,
    "barom_rel_mmhg": 762.89,
    "barom_abs_mmhg": 620.75,
    "hourly_rain_mm": 0.0,
    "daily_rain_mm": 0.0,
    "weekly_rain_mm": 37.34,
    "monthly_rain_mm": 87.12,
    "yearly_rain_mm": 147.07,
    "event_rain_mm": 0.0,
    "total_rain_mm": 147.09,
    "uv": 2,
    "solar_radiation": 239.59,
    "battout": 1,
    "date": "2026-02-04T21:05:00.000Z",
    "date_utc": 1770239100000,
}


class DailyReadingResponse(BaseModel):
    """A single weather station reading with all sensor data converted to metric units."""

    id: int = Field(description="Unique reading identifier", examples=[42])
    timestamp: datetime = Field(
        description="UTC timestamp when the reading was collected",
        examples=["2026-02-04T21:05:00Z"],
    )
    data: dict = Field(
        description="Converted sensor data with metric units. "
        "Use /api/history/fields for field descriptions and units.",
        examples=[READING_DATA_EXAMPLE],
    )

    model_config = {"from_attributes": True}

    @field_validator("data", mode="before")
    @classmethod
    def _sanitize_data(cls, value):
        if isinstance(value, dict):
            return strip_sensitive_fields(value)
        return value


class FieldDescription(BaseModel):
    """Metadata describing a single sensor field."""

    description: str = Field(
        description="Human-readable description of the field",
        examples=["Outdoor Temperature"],
    )
    unit: str = Field(
        description="Unit of measurement",
        examples=["°C"],
    )


class PaginatedDailyResponse(BaseModel):
    """Paginated list of weather station readings."""

    items: list[DailyReadingResponse] = Field(description="List of readings for the current page")
    total: int = Field(description="Total number of readings matching the query", examples=[250])
    limit: int = Field(description="Maximum number of readings per page", examples=[100])
    offset: int = Field(description="Number of readings skipped from the start", examples=[0])


class MetricStatistics(BaseModel):
    """Summary statistics for a metric."""

    min: float | None = None
    avg: float | None = None
    max: float | None = None


class DayExtreme(BaseModel):
    """A day-level extreme value for a metric."""

    date: str = Field(description="UTC date in YYYY-MM-DD format", examples=["2026-02-04"])
    value: float = Field(description="Extreme metric value for that day", examples=[27.4])


class TemperatureStatistics(MetricStatistics):
    hottest_day: DayExtreme | None = None
    coldest_day: DayExtreme | None = None


class RainStatistics(MetricStatistics):
    wettest_day: DayExtreme | None = None


class WindStatistics(MetricStatistics):
    day_with_most_wind: DayExtreme | None = None
    strongest_wind: DayExtreme | None = None


class SolarRadiationStatistics(MetricStatistics):
    brightest_day: DayExtreme | None = None
    darkest_day: DayExtreme | None = None


class HumidityStatistics(MetricStatistics):
    most_humid_day: DayExtreme | None = None
    least_humid_day: DayExtreme | None = None


class ReadingStatistics(BaseModel):
    """Aggregate statistics computed from retained readings for a station."""

    sample_count: int = Field(description="Number of readings included in the statistics", examples=[10512])
    range_start: datetime | None = Field(
        default=None,
        description="Oldest reading timestamp included in the stats (UTC).",
    )
    range_end: datetime | None = Field(
        default=None,
        description="Newest reading timestamp included in the stats (UTC).",
    )
    temperature: TemperatureStatistics = Field(default_factory=TemperatureStatistics)
    rain: RainStatistics = Field(default_factory=RainStatistics)
    wind: WindStatistics = Field(default_factory=WindStatistics)
    solar_radiation: SolarRadiationStatistics = Field(default_factory=SolarRadiationStatistics)
    humidity: HumidityStatistics = Field(default_factory=HumidityStatistics)


class LatestReadingResponse(BaseModel):
    """Latest reading plus aggregate statistics."""

    reading: DailyReadingResponse
    statistics: ReadingStatistics


class TwilightPeriod(BaseModel):
    """Twilight, blue hour, and golden hour times for morning or evening."""

    astronomical_twilight_begin: str | None = None
    astronomical_twilight_end: str | None = None
    nautical_twilight_begin: str | None = None
    nautical_twilight_end: str | None = None
    civil_twilight_begin: str | None = None
    civil_twilight_end: str | None = None
    blue_hour_begin: str | None = None
    blue_hour_end: str | None = None
    golden_hour_begin: str | None = None
    golden_hour_end: str | None = None


class AstronomyResponse(BaseModel):
    """Sun and moon data from ipgeolocation.io."""

    current_time: str | None = None
    date: str | None = None
    sunrise: str | None = None
    sunset: str | None = None
    solar_noon: str | None = None
    mid_night: str | None = None
    day_length: str | None = None
    sun_altitude: float | None = None
    sun_azimuth: float | None = None
    sun_distance: float | None = None
    sun_status: str | None = None
    moonrise: str | None = None
    moonset: str | None = None
    moon_altitude: float | None = None
    moon_azimuth: float | None = None
    moon_distance: float | None = None
    moon_parallactic_angle: float | None = None
    moon_phase: str | None = None
    moon_illumination_percentage: str | None = None
    moon_angle: float | None = None
    moon_status: str | None = None
    night_begin: str | None = None
    night_end: str | None = None
    morning: TwilightPeriod | None = None
    evening: TwilightPeriod | None = None
