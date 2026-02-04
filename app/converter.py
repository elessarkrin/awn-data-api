"""Imperial to metric unit conversions for Ambient Weather data."""

from typing import Any


def fahrenheit_to_celsius(f: float) -> float:
    return round((f - 32) * 5 / 9, 2)


def mph_to_kmh(mph: float) -> float:
    return round(mph * 1.60934, 2)


def inhg_to_hpa(inhg: float) -> float:
    return round(inhg * 33.8639, 2)


def inches_to_mm(inches: float) -> float:
    return round(inches * 25.4, 2)


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
    # Pressure: inHg -> hPa
    "baromrelin": ("barom_rel_hpa", inhg_to_hpa),
    "baromabsin": ("barom_abs_hpa", inhg_to_hpa),
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
EXCLUDED_FIELDS = {"macAddress", "device", "loc", "lastRain"}

# Numeric metric names eligible for aggregation (exclude non-numeric / metadata fields)
NON_NUMERIC_FIELDS = {"date", "date_utc", "tz"}


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

    return converted


def get_numeric_fields(data: dict) -> dict[str, float]:
    """Extract only the numeric fields suitable for aggregation."""
    return {
        k: v
        for k, v in data.items()
        if isinstance(v, (int, float)) and k not in NON_NUMERIC_FIELDS
    }
