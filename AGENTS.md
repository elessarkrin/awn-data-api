# AGENTS.md

Repository guidance for coding agents.

## Scope

- Applies to the whole repository.
- Keep changes focused and minimal.
- Do not add or commit secrets (`.env`, keys, tokens, credentials).

## Project Overview

- FastAPI backend for Ambient Weather data.
- Data model: `app/database.py` (`DailyReading`).
- Collector and storage: `app/collector.py`.
- Unit conversion and field metadata: `app/converter.py`.
- Statistics engine: `app/statistics.py`.
- API routes: `app/routes/*`.

## Current API Behavior (Important)

- `/api/history/latest` returns:
  - `reading`: latest reading payload.
  - `statistics`: aggregate station stats over retained data.
- `/api/stream` returns SSE `reading` events with the same shape (`reading` + `statistics`).
- `/api/stream` emits:
  - On live updates.
  - Periodic snapshots every `SSE_EMIT_INTERVAL_SECONDS` (default `60`).
- `/api/astronomy` cache:
  - 5-minute UTC buckets (`:00`, `:05`, ...).
  - Uses stale cache if upstream fetch fails.
- API gzip compression enabled via `GZipMiddleware`.

## Config Keys

Primary runtime config is in `app/config.py`. Keep docs and `.env.example` aligned with code when adding keys.

Notable keys:

- `COLLECTION_INTERVAL_SECONDS`
- `DAILY_RETENTION_DAYS`
- `BACKFILL_DAYS`
- `BACKFILL_BATCH_SIZE`
- `BACKFILL_REQUEST_DELAY`
- `ASTRONOMY_API_KEY`, `LAT`, `LON`
- `REACT_BUILD_DIR`
- `GZIP_MINIMUM_SIZE`, `GZIP_COMPRESSLEVEL`
- `SSE_EMIT_INTERVAL_SECONDS`

## Validation

Before committing, run targeted checks for touched modules.

```bash
python -m compileall app main.py
```

If route behavior changes, run a minimal runtime smoke check using ASGI/httpx or existing local scripts.

## Documentation

When behavior changes, update all of:

- `README.md`
- `.env.example`
- `AGENTS.md`
- `CLAUDE.md`

## Commit Rules

- Keep commits scoped and descriptive.
- Do not include unrelated file churn.
- `nul` must remain ignored/untracked.
