"""Imperial to metric unit conversions for Ambient Weather data."""

import math
from typing import Any


def fahrenheit_to_celsius(f: float) -> float:
    return round((f - 32) * 5 / 9, 2)


def mph_to_kmh(mph: float) -> float:
    return round(mph * 1.60934, 2)


def inhg_to_mmhg(inhg: float) -> float:
    return round(inhg * 25.4, 2)


def inches_to_mm(inches: float) -> float:
    return round(inches * 25.4, 2)


def calculate_vpd_kpa(temp_c: float, humidity: float) -> float:
    """Calculate Vapor Pressure Deficit (kPa) from temperature and relative humidity.

    Formula:
    - es = 0.6108 * exp((17.27 * T) / (T + 237.3))
    - ea = es * (RH / 100)
    - vpd = es - ea
    """
    clamped_humidity = max(0.0, min(100.0, humidity))
    saturation_vapor_pressure = 0.6108 * math.exp((17.27 * temp_c) / (temp_c + 237.3))
    actual_vapor_pressure = saturation_vapor_pressure * (clamped_humidity / 100.0)
    return round(saturation_vapor_pressure - actual_vapor_pressure, 3)


def calculate_absolute_humidity(temp_c: float, humidity: float) -> float:
    """Calculate Absolute Humidity (g/m³) from temperature and relative humidity.

    Formula: AH = (6.112 * exp(17.67 * T / (T + 243.5)) * RH * 2.1674) / (273.15 + T)
    """
    clamped_humidity = max(0.0, min(100.0, humidity))
    numerator = 6.112 * math.exp((17.67 * temp_c) / (temp_c + 243.5)) * clamped_humidity * 2.1674
    return round(numerator / (273.15 + temp_c), 2)


def calculate_beaufort_scale(wind_speed_kmh: float) -> int:
    """Convert wind speed (km/h) to Beaufort scale (0-12)."""
    speed = max(0.0, wind_speed_kmh)
    if speed < 1:
        return 0
    if speed <= 5:
        return 1
    if speed <= 11:
        return 2
    if speed <= 19:
        return 3
    if speed <= 28:
        return 4
    if speed <= 38:
        return 5
    if speed <= 49:
        return 6
    if speed <= 61:
        return 7
    if speed <= 74:
        return 8
    if speed <= 88:
        return 9
    if speed <= 102:
        return 10
    if speed <= 117:
        return 11
    return 12


# Mapping: original_field -> (metric_field_name, conversion_function_or_None)
FIELD_CONVERSIONS: dict[str, tuple[str, Any]] = {
    # Temperature: degF -> degC
    "tempf": ("temp_c", fahrenheit_to_celsius),
    "tempinf": ("temp_in_c", fahrenheit_to_celsius),
    "temp1f": ("temp1_c", fahrenheit_to_celsius),
    "temp2f": ("temp2_c", fahrenheit_to_celsius),
    "temp3f": ("temp3_c", fahrenheit_to_celsius),
    "temp4f": ("temp4_c", fahrenheit_to_celsius),
    "temp5f": ("temp5_c", fahrenheit_to_celsius),
    "temp6f": ("temp6_c", fahrenheit_to_celsius),
    "temp7f": ("temp7_c", fahrenheit_to_celsius),
    "temp8f": ("temp8_c", fahrenheit_to_celsius),
    "temp9f": ("temp9_c", fahrenheit_to_celsius),
    "temp10f": ("temp10_c", fahrenheit_to_celsius),
    "feelsLike": ("feels_like_c", fahrenheit_to_celsius),
    "feelsLikein": ("feels_like_in_c", fahrenheit_to_celsius),
    "feelsLike1": ("feels_like1_c", fahrenheit_to_celsius),
    "feelsLike2": ("feels_like2_c", fahrenheit_to_celsius),
    "feelsLike3": ("feels_like3_c", fahrenheit_to_celsius),
    "feelsLike4": ("feels_like4_c", fahrenheit_to_celsius),
    "feelsLike5": ("feels_like5_c", fahrenheit_to_celsius),
    "feelsLike6": ("feels_like6_c", fahrenheit_to_celsius),
    "feelsLike7": ("feels_like7_c", fahrenheit_to_celsius),
    "feelsLike8": ("feels_like8_c", fahrenheit_to_celsius),
    "feelsLike9": ("feels_like9_c", fahrenheit_to_celsius),
    "feelsLike10": ("feels_like10_c", fahrenheit_to_celsius),
    "dewPoint": ("dew_point_c", fahrenheit_to_celsius),
    "dewPointin": ("dew_point_in_c", fahrenheit_to_celsius),
    "dewPoint1": ("dew_point1_c", fahrenheit_to_celsius),
    "dewPoint2": ("dew_point2_c", fahrenheit_to_celsius),
    "dewPoint3": ("dew_point3_c", fahrenheit_to_celsius),
    "dewPoint4": ("dew_point4_c", fahrenheit_to_celsius),
    "dewPoint5": ("dew_point5_c", fahrenheit_to_celsius),
    "dewPoint6": ("dew_point6_c", fahrenheit_to_celsius),
    "dewPoint7": ("dew_point7_c", fahrenheit_to_celsius),
    "dewPoint8": ("dew_point8_c", fahrenheit_to_celsius),
    "dewPoint9": ("dew_point9_c", fahrenheit_to_celsius),
    "dewPoint10": ("dew_point10_c", fahrenheit_to_celsius),
    # Wind speed: mph -> km/h
    "windspeedmph": ("wind_speed_kmh", mph_to_kmh),
    "windgustmph": ("wind_gust_kmh", mph_to_kmh),
    "maxdailygust": ("max_daily_gust_kmh", mph_to_kmh),
    "windspdmph_avg2m": ("wind_speed_avg_2m_kmh", mph_to_kmh),
    "windspdmph_avg10m": ("wind_speed_avg_10m_kmh", mph_to_kmh),
    # Pressure: inHg -> mmHg
    "baromrelin": ("barom_rel_mmhg", inhg_to_mmhg),
    "baromabsin": ("barom_abs_mmhg", inhg_to_mmhg),
    # Rainfall: inches -> mm
    "hourlyrainin": ("hourly_rain_mm", inches_to_mm),
    "dailyrainin": ("daily_rain_mm", inches_to_mm),
    "weeklyrainin": ("weekly_rain_mm", inches_to_mm),
    "monthlyrainin": ("monthly_rain_mm", inches_to_mm),
    "yearlyrainin": ("yearly_rain_mm", inches_to_mm),
    "eventrainin": ("event_rain_mm", inches_to_mm),
    "totalrainin": ("total_rain_mm", inches_to_mm),
    "24hourrainin": ("rain_24h_mm", inches_to_mm),
    # Pass-through with renamed keys
    "humidity": ("humidity", None),
    "humidityin": ("humidity_in", None),
    "humidity1": ("humidity1", None),
    "humidity2": ("humidity2", None),
    "humidity3": ("humidity3", None),
    "humidity4": ("humidity4", None),
    "humidity5": ("humidity5", None),
    "humidity6": ("humidity6", None),
    "humidity7": ("humidity7", None),
    "humidity8": ("humidity8", None),
    "humidity9": ("humidity9", None),
    "humidity10": ("humidity10", None),
    "winddir": ("wind_dir", None),
    "windgustdir": ("wind_gust_dir", None),
    "winddir_avg2m": ("wind_dir_avg_2m", None),
    "winddir_avg10m": ("wind_dir_avg_10m", None),
    "uv": ("uv", None),
    "solarradiation": ("solar_radiation", None),
    "date": ("date", None),
    "dateutc": ("date_utc", None),
    "tz": ("tz", None),
}

# Fields to exclude from the converted output (metadata, not sensor data)
EXCLUDED_FIELDS = {
    "macAddress",
    "mac_address",
    "station_mac",
    "stationMac",
    "device",
    "loc",
    "lastRain",
}

_SENSITIVE_KEY_NORMALIZED = {"mac", "macaddress", "stationmac"}

# Descriptions for fields currently returned by the station
FIELD_DESCRIPTIONS: dict[str, dict[str, str]] = {
    # Temperature (°C)
    "temp_c": {"description": "Outdoor Temperature", "unit": "°C"},
    "temp_in_c": {"description": "Indoor Temperature", "unit": "°C"},
    "feels_like_c": {"description": "Outdoor Feels Like (Wind Chill if <10°C, Heat Index if >20°C)", "unit": "°C"},
    "feels_like_in_c": {"description": "Indoor Feels Like", "unit": "°C"},
    "dew_point_c": {"description": "Outdoor Dew Point", "unit": "°C"},
    "dew_point_in_c": {"description": "Indoor Dew Point", "unit": "°C"},
    # Wind (km/h and degrees)
    "wind_speed_kmh": {"description": "Instantaneous wind speed", "unit": "km/h"},
    "beaufort_scale": {"description": "Wind force category from wind_speed_kmh (0-12)", "unit": "scale"},
    "wind_gust_kmh": {"description": "Max wind speed in the last 10 minutes", "unit": "km/h"},
    "max_daily_gust_kmh": {"description": "Maximum wind speed in last day", "unit": "km/h"},
    "wind_dir": {"description": "Instantaneous wind direction", "unit": "°"},
    # Pressure (mmHg)
    "barom_rel_mmhg": {"description": "Relative Pressure", "unit": "mmHg"},
    "barom_abs_mmhg": {"description": "Absolute Pressure", "unit": "mmHg"},
    # Rainfall (mm)
    "hourly_rain_mm": {"description": "Hourly Rain Rate", "unit": "mm/hr"},
    "daily_rain_mm": {"description": "Daily Rain", "unit": "mm"},
    "weekly_rain_mm": {"description": "Weekly Rain", "unit": "mm"},
    "monthly_rain_mm": {"description": "Monthly Rain", "unit": "mm"},
    "yearly_rain_mm": {"description": "Yearly Rain", "unit": "mm"},
    "event_rain_mm": {"description": "Event Rain", "unit": "mm"},
    "total_rain_mm": {"description": "Total Rain since last factory reset", "unit": "mm"},
    # Humidity (%)
    "humidity": {"description": "Outdoor Humidity", "unit": "%"},
    "humidity_in": {"description": "Indoor Humidity", "unit": "%"},
    "vpd_kpa": {"description": "Vapor Pressure Deficit (derived from temp_c and humidity)", "unit": "kPa"},
    "abs_humidity_gm3": {"description": "Absolute Humidity (derived from temp_c and humidity)", "unit": "g/m³"},
    # UV & Solar
    "uv": {"description": "Ultra-Violet Radiation Index", "unit": "index"},
    "solar_radiation": {"description": "Solar Radiation", "unit": "W/m²"},
    # Battery
    "battout": {"description": "Outdoor Battery", "unit": "1=OK, 0=Low"},
    # Metadata
    "date": {"description": "Human readable date", "unit": "ISO 8601"},
    "date_utc": {"description": "Datetime in milliseconds from epoch", "unit": "ms"},
}


# Fields that should use max() when aggregating daily summaries
MAX_FIELDS = {
    "wind_gust_kmh",
    "max_daily_gust_kmh",
    "beaufort_scale",
    "uv",
    "solar_radiation",
    "daily_rain_mm",
    "weekly_rain_mm",
    "monthly_rain_mm",
    "yearly_rain_mm",
    "event_rain_mm",
    "total_rain_mm",
    "rain_24h_mm",
    "hourly_rain_mm",
}

# Fields that should use min() when aggregating daily summaries
MIN_FIELDS: set[str] = set()

# Fields to exclude from aggregation (non-numeric or metadata)
SKIP_FIELDS = {"date", "date_utc", "tz", "battout"}


def add_derived_metrics(reading: dict) -> dict:
    """Add derived metrics to a reading when required source fields are present."""
    enriched = dict(reading)
    temp_c = enriched.get("temp_c")
    humidity = enriched.get("humidity")
    wind_speed_kmh = enriched.get("wind_speed_kmh")

    if isinstance(temp_c, (int, float)) and isinstance(humidity, (int, float)):
        enriched["vpd_kpa"] = calculate_vpd_kpa(float(temp_c), float(humidity))
        enriched["abs_humidity_gm3"] = calculate_absolute_humidity(float(temp_c), float(humidity))
    if isinstance(wind_speed_kmh, (int, float)):
        enriched["beaufort_scale"] = calculate_beaufort_scale(float(wind_speed_kmh))

    return enriched


def strip_sensitive_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove MAC-address-like metadata keys from a payload."""
    sanitized: dict[str, Any] = {}
    for key, value in payload.items():
        normalized = "".join(ch for ch in key.lower() if ch.isalnum())
        if normalized in _SENSITIVE_KEY_NORMALIZED:
            continue
        sanitized[key] = value
    return sanitized


def convert_reading(raw_data: dict) -> dict:
    """Convert a raw AWN reading from imperial to metric units.

    Fields with known conversions are converted and renamed.
    Unknown numeric fields are passed through with their original key.
    Excluded metadata fields are dropped.
    """
    converted = {}

    for key, value in raw_data.items():
        if key in EXCLUDED_FIELDS:
            continue

        if key in FIELD_CONVERSIONS:
            metric_key, converter_fn = FIELD_CONVERSIONS[key]
            if converter_fn is not None and isinstance(value, (int, float)):
                converted[metric_key] = converter_fn(value)
            else:
                converted[metric_key] = value
        else:
            # Pass through unknown fields as-is
            converted[key] = value

    return add_derived_metrics(strip_sensitive_fields(converted))
