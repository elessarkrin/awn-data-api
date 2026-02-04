"""Imperial to metric unit conversions for Ambient Weather data."""

from typing import Any


def fahrenheit_to_celsius(f: float) -> float:
    return round((f - 32) * 5 / 9, 2)


def mph_to_kmh(mph: float) -> float:
    return round(mph * 1.60934, 2)


def inhg_to_mmhg(inhg: float) -> float:
    return round(inhg * 25.4, 2)


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
EXCLUDED_FIELDS = {"macAddress", "device", "loc", "lastRain"}

# Descriptions for each converted field, used by the /fields endpoint
FIELD_DESCRIPTIONS: dict[str, dict[str, str]] = {
    # Temperature (°C)
    "temp_c": {"description": "Outdoor Temperature", "unit": "°C"},
    "temp_in_c": {"description": "Indoor Temperature", "unit": "°C"},
    "temp1_c": {"description": "Temperature Sensor 1", "unit": "°C"},
    "temp2_c": {"description": "Temperature Sensor 2", "unit": "°C"},
    "temp3_c": {"description": "Temperature Sensor 3", "unit": "°C"},
    "temp4_c": {"description": "Temperature Sensor 4", "unit": "°C"},
    "temp5_c": {"description": "Temperature Sensor 5", "unit": "°C"},
    "temp6_c": {"description": "Temperature Sensor 6", "unit": "°C"},
    "temp7_c": {"description": "Temperature Sensor 7", "unit": "°C"},
    "temp8_c": {"description": "Temperature Sensor 8", "unit": "°C"},
    "temp9_c": {"description": "Temperature Sensor 9", "unit": "°C"},
    "temp10_c": {"description": "Temperature Sensor 10", "unit": "°C"},
    "feels_like_c": {"description": "Outdoor Feels Like (Wind Chill if <10°C, Heat Index if >20°C)", "unit": "°C"},
    "feels_like_in_c": {"description": "Indoor Feels Like", "unit": "°C"},
    "feels_like1_c": {"description": "Feels Like Sensor 1", "unit": "°C"},
    "feels_like2_c": {"description": "Feels Like Sensor 2", "unit": "°C"},
    "feels_like3_c": {"description": "Feels Like Sensor 3", "unit": "°C"},
    "feels_like4_c": {"description": "Feels Like Sensor 4", "unit": "°C"},
    "feels_like5_c": {"description": "Feels Like Sensor 5", "unit": "°C"},
    "feels_like6_c": {"description": "Feels Like Sensor 6", "unit": "°C"},
    "feels_like7_c": {"description": "Feels Like Sensor 7", "unit": "°C"},
    "feels_like8_c": {"description": "Feels Like Sensor 8", "unit": "°C"},
    "feels_like9_c": {"description": "Feels Like Sensor 9", "unit": "°C"},
    "feels_like10_c": {"description": "Feels Like Sensor 10", "unit": "°C"},
    "dew_point_c": {"description": "Outdoor Dew Point", "unit": "°C"},
    "dew_point_in_c": {"description": "Indoor Dew Point", "unit": "°C"},
    "dew_point1_c": {"description": "Dew Point Sensor 1", "unit": "°C"},
    "dew_point2_c": {"description": "Dew Point Sensor 2", "unit": "°C"},
    "dew_point3_c": {"description": "Dew Point Sensor 3", "unit": "°C"},
    "dew_point4_c": {"description": "Dew Point Sensor 4", "unit": "°C"},
    "dew_point5_c": {"description": "Dew Point Sensor 5", "unit": "°C"},
    "dew_point6_c": {"description": "Dew Point Sensor 6", "unit": "°C"},
    "dew_point7_c": {"description": "Dew Point Sensor 7", "unit": "°C"},
    "dew_point8_c": {"description": "Dew Point Sensor 8", "unit": "°C"},
    "dew_point9_c": {"description": "Dew Point Sensor 9", "unit": "°C"},
    "dew_point10_c": {"description": "Dew Point Sensor 10", "unit": "°C"},
    # Wind (km/h and degrees)
    "wind_speed_kmh": {"description": "Instantaneous wind speed", "unit": "km/h"},
    "wind_gust_kmh": {"description": "Max wind speed in the last 10 minutes", "unit": "km/h"},
    "max_daily_gust_kmh": {"description": "Maximum wind speed in last day", "unit": "km/h"},
    "wind_speed_avg_2m_kmh": {"description": "Average wind speed, 2 minute average", "unit": "km/h"},
    "wind_speed_avg_10m_kmh": {"description": "Average wind speed, 10 minute average", "unit": "km/h"},
    "wind_dir": {"description": "Instantaneous wind direction", "unit": "°"},
    "wind_gust_dir": {"description": "Wind direction at which the wind gust occurred", "unit": "°"},
    "wind_dir_avg_2m": {"description": "Average wind direction, 2 minute average", "unit": "°"},
    "wind_dir_avg_10m": {"description": "Average wind direction, 10 minute average", "unit": "°"},
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
    "rain_24h_mm": {"description": "24 Hour Rain", "unit": "mm"},
    # Humidity (%)
    "humidity": {"description": "Outdoor Humidity", "unit": "%"},
    "humidity_in": {"description": "Indoor Humidity", "unit": "%"},
    "humidity1": {"description": "Humidity Sensor 1", "unit": "%"},
    "humidity2": {"description": "Humidity Sensor 2", "unit": "%"},
    "humidity3": {"description": "Humidity Sensor 3", "unit": "%"},
    "humidity4": {"description": "Humidity Sensor 4", "unit": "%"},
    "humidity5": {"description": "Humidity Sensor 5", "unit": "%"},
    "humidity6": {"description": "Humidity Sensor 6", "unit": "%"},
    "humidity7": {"description": "Humidity Sensor 7", "unit": "%"},
    "humidity8": {"description": "Humidity Sensor 8", "unit": "%"},
    "humidity9": {"description": "Humidity Sensor 9", "unit": "%"},
    "humidity10": {"description": "Humidity Sensor 10", "unit": "%"},
    # UV & Solar
    "uv": {"description": "Ultra-Violet Radiation Index", "unit": "index"},
    "solar_radiation": {"description": "Solar Radiation", "unit": "W/m²"},
    # Metadata
    "date": {"description": "Human readable date", "unit": "ISO 8601"},
    "date_utc": {"description": "Datetime in milliseconds from epoch", "unit": "ms"},
    "tz": {"description": "IANA Time Zone", "unit": "string"},
}


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
