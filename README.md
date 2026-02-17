# AWN Data API

REST API service that collects weather data from the [Ambient Weather Network (AWN) API](https://ambientweather.docs.apiary.io/), converts measurements to metric units, stores data in SQLite, and exposes history, live stream, and astronomy endpoints.

## Features

- Polls AWN data on a configurable interval and stores normalized readings.
- Backfills up to one year of historical data on startup.
- Serves paginated history and date-range queries.
- Serves latest reading with station-wide aggregate statistics.
- Streams live SSE updates and periodic SSE snapshots.
- Provides astronomy data with 5-minute cache and stale fallback on upstream errors.
- Serves an optional React build at `/app`.
- Supports gzip compression for API responses.

## API Endpoints

All API routes are under `/api` (except `/health` and `/app`).

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Service health check |
| GET | `/api/history` | Paginated historical readings |
| GET | `/api/history/latest` | Latest reading plus aggregate statistics |
| GET | `/api/history/range` | Date-range readings (aggregates for large ranges) |
| GET | `/api/history/fields` | Field metadata and units |
| GET | `/api/stream` | SSE stream with reading + statistics payloads |
| GET | `/api/astronomy` | Sun/moon data (5-minute cache, stale fallback) |
| GET | `/app` | React SPA build (served from `REACT_BUILD_DIR`) |

## Latest and Stream Payload

`/api/history/latest` and `/api/stream` return payloads with this shape:

```json
{
  "reading": {
    "temp_c": 19.11,
    "humidity": 78,
    "wind_speed_kmh": 6.49
  },
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

## SSE Behavior

- On connection: an immediate snapshot `reading` event is sent.
- Live mode: a `reading` event is sent whenever a new reading is collected.
- Periodic mode: a snapshot `reading` event is also sent every `SSE_EMIT_INTERVAL_SECONDS` (default `60`).

## Response Compression

When clients send `Accept-Encoding: gzip`, API responses are gzip-compressed.

## Docker

### Files

- `Dockerfile`: container image definition.
- `docker/entrypoint.sh`: startup flow (backfill before server).
- `docker-compose.yml`: optional local orchestration with source mount.
- `.dockerignore`: excludes local/dev artifacts from image build context.

### Startup Flow

Container startup order:

1. Run backfill command (default: `python backfill.py`).
2. If backfill succeeds (or `BACKFILL_STRICT=0`), start `uvicorn`.
3. Serve API on configured host/port.

### Build

```bash
docker build -t awn-data-api:latest .
```

### Run (mount app source + persist SQLite)

```bash
docker run --rm -it \
  --env-file .env \
  -p 8000:8000 \
  -v "$(pwd):/app" \
  -v awn_data:/data \
  awn-data-api:latest
```

### Run With Compose

```bash
docker compose up --build
```

### Docker Runtime Variables

| Variable | Description | Default |
|---|---|---|
| `RUN_BACKFILL_BEFORE_START` | Run backfill before server start (`1` or `0`) | `1` |
| `BACKFILL_STRICT` | Exit container if backfill fails (`1` or `0`) | `0` |
| `BACKFILL_CMD` | Command used to perform backfill | `python backfill.py` |
| `PRE_START_CMD` | Optional command to run after backfill and before server | empty |
| `UVICORN_APP` | ASGI app target | `main:app` |
| `UVICORN_HOST` | Bind host | `0.0.0.0` |
| `UVICORN_PORT` | Bind port | `8000` |
| `UVICORN_WORKERS` | Number of uvicorn workers | `1` |
| `UVICORN_LOG_LEVEL` | Uvicorn log level | `info` |
| `UVICORN_RELOAD` | Enable reload (`1` or `0`) | `0` |
| `UVICORN_EXTRA_ARGS` | Extra args appended to uvicorn command | empty |

By default in Docker, SQLite is written to:

- `sqlite+aiosqlite:////data/weather.db`

Override with `DATABASE_URL` if needed.


## Setup

### Prerequisites

- Python 3.10+
- Ambient Weather account with API/Application keys

### Installation

```bash
pip install -e .
```

### Configuration

Copy and edit env file:

```bash
cp .env.example .env
```

| Variable | Description | Default |
|---|---|---|
| `AWN_API_KEY` | Ambient Weather API key | empty |
| `AWN_APPLICATION_KEY` | Ambient Weather application key | empty |
| `AWN_MAC_ADDRESS` | Station MAC address | empty |
| `COLLECTION_INTERVAL_SECONDS` | Reading poll interval (seconds) | `60` |
| `DAILY_RETENTION_DAYS` | Retention period for stored readings | `365` |
| `BACKFILL_DAYS` | Startup backfill window (days) | `365` |
| `BACKFILL_BATCH_SIZE` | Records fetched per backfill request | `288` |
| `BACKFILL_REQUEST_DELAY` | Delay between backfill requests (seconds) | `1.1` |
| `DATABASE_URL` | SQLAlchemy async DB URL | `sqlite+aiosqlite:///./weather.db` |
| `CORS_ALLOW_ORIGINS` | Allowed browser origins (comma-separated or JSON list) | `http://localhost:5173,http://localhost:5174` |
| `CORS_ALLOW_CREDENTIALS` | Allow credentialed CORS requests | `true` |
| `ASTRONOMY_API_KEY` | ipgeolocation astronomy API key | empty |
| `LAT` | Astronomy latitude | empty |
| `LON` | Astronomy longitude | empty |
| `REACT_BUILD_DIR` | Path to React build served at `/app` | `frontend/dist` |
| `GZIP_MINIMUM_SIZE` | Minimum response size for gzip (bytes) | `500` |
| `GZIP_COMPRESSLEVEL` | Gzip compression level (1-9) | `6` |
| `SSE_EMIT_INTERVAL_SECONDS` | Periodic SSE snapshot interval (seconds) | `60` |

### Run

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Assistant Docs

- `AGENTS.md` contains general coding-agent guidance for this repository.
- `CLAUDE.md` contains Claude-specific collaboration guidance.
