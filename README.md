# AWN Data API

REST API service that collects weather data from the [Ambient Weather Network (AWN) API](https://ambientweather.docs.apiary.io/), converts all measurements to metric units, and stores them in a local SQLite database. It also serves as a queryable API for both real-time and historical weather data.

This project is tuned to work with the **WS-2902 Weather Station**.

## How It Works

The service polls the AWN REST API every 60 seconds (configurable), converts incoming imperial readings to metric, computes additional derived metrics, and persists everything into SQLite. On startup, it backfills up to one year of historical data automatically.

### Unit Conversions

All raw AWN values are converted at ingestion time:

| Measurement | From       | To     |
|-------------|------------|--------|
| Temperature | °F         | °C     |
| Wind Speed  | mph        | km/h   |
| Pressure    | inHg       | mmHg   |
| Rainfall    | inches     | mm     |

### Inferred Metrics

In addition to the direct conversions above, the service computes the following derived metrics from the collected data:

- **Vapor Pressure Deficit (VPD)** — measured in kPa, calculated from outdoor temperature and humidity using the Tetens formula. VPD indicates the drying power of the air and is useful for agriculture and plant science.
- **Absolute Humidity** — measured in g/m³, derived from outdoor temperature and humidity. Represents the actual mass of water vapor per unit volume of air.
- **Beaufort Scale** — an integer from 0 to 12, derived from wind speed in km/h. Categorizes wind force from calm (0) to hurricane-force (12).

## API Endpoints

All endpoints are served under `/api` with interactive docs available at `/docs`.

| Method | Path                    | Description                                                    |
|--------|-------------------------|----------------------------------------------------------------|
| GET    | `/health`               | Service health check                                           |
| GET    | `/api/history`          | Paginated historical readings with optional date range filters |
| GET    | `/api/history/latest`   | Most recent reading plus aggregate statistics                  |
| GET    | `/api/history/range`    | Readings for a date range (auto-aggregates for ranges > 30 days) |
| GET    | `/api/history/fields`   | Field metadata (descriptions and units for all sensor fields)  |
| GET    | `/api/stream`           | Real-time readings via SSE (reading + statistics payloads)     |
| GET    | `/api/astronomy`        | Sun/moon data (5-minute UTC cache with stale fallback)         |
| GET    | `/app`                  | React web app build (serves `index.html` with SPA fallback)    |

### Latest + Stream Statistics Payload

`/api/history/latest` and `/api/stream` include statistics computed across all retained readings
for the selected station (by default: the configured station).

Payload shape:

```json
{
  "reading": { "...": "latest metric fields" },
  "statistics": {
    "sample_count": 10512,
    "range_start": "2025-02-17T00:00:00Z",
    "range_end": "2026-02-16T15:35:00Z",
    "temperature": {
      "min": 1.2,
      "avg": 14.7,
      "max": 33.1,
      "hottest_day": {"date": "2025-08-09", "value": 33.1},
      "coldest_day": {"date": "2026-01-14", "value": 1.2}
    },
    "rain": {
      "min": 0.0,
      "avg": 1.4,
      "max": 42.7,
      "wettest_day": {"date": "2025-11-03", "value": 42.7}
    },
    "wind": {
      "min": 0.0,
      "avg": 9.8,
      "max": 54.2,
      "day_with_most_wind": {"date": "2025-12-12", "value": 23.5},
      "strongest_wind": {"date": "2025-12-12", "value": 54.2}
    },
    "solar_radiation": {
      "min": 0.0,
      "avg": 178.4,
      "max": 1012.0,
      "brightest_day": {"date": "2025-07-02", "value": 482.7},
      "darkest_day": {"date": "2025-12-21", "value": 39.4}
    },
    "humidity": {
      "min": 15.0,
      "avg": 63.2,
      "max": 99.0,
      "most_humid_day": {"date": "2025-10-20", "value": 88.4},
      "least_humid_day": {"date": "2025-06-29", "value": 39.2}
    }
  }
}
```

## Setup

### Prerequisites

- Python 3.10+
- An [Ambient Weather](https://ambientweather.net/) account with API and Application keys

### Installation

```bash
pip install -e .
```

### Configuration

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

| Variable                     | Description                                  | Default                     |
|------------------------------|----------------------------------------------|-----------------------------|
| `AWN_API_KEY`                | Your AWN API key                             | —                           |
| `AWN_APPLICATION_KEY`        | Your AWN Application key                     | —                           |
| `AWN_MAC_ADDRESS`            | MAC address of your weather station          | —                           |
| `COLLECTION_INTERVAL_SECONDS`| Polling interval in seconds                  | `60`                        |
| `DAILY_RETENTION_DAYS`       | Days to keep readings before purging         | `365`                       |
| `BACKFILL_DAYS`              | Days of history to backfill on startup       | `365`                       |
| `DATABASE_URL`               | SQLAlchemy async database URL                | `sqlite+aiosqlite:///./weather.db` |
| `CORS_ALLOW_ORIGINS`         | Comma-separated allowed CORS origins         | `http://localhost:5173`     |
| `REACT_BUILD_DIR`            | React build output directory served at `/app`| `frontend/dist`             |

### Running

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

If no API credentials are configured, the service runs in **mock mode**, generating realistic random weather data for development and testing.

## Tech Stack

- **FastAPI** — async web framework
- **SQLAlchemy** (async) + **aiosqlite** — database ORM and SQLite driver
- **httpx** — async HTTP client for AWN API calls
- **Pydantic** — data validation and settings management
