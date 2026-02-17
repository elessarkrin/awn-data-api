# CLAUDE.md

Claude collaboration notes for this repository.

## Quick Context

- Framework: FastAPI
- Storage: SQLite via SQLAlchemy async
- Live delivery: SSE (`/api/stream`)
- Statistics: computed in `app/statistics.py`

## High-Impact Files

- `main.py`: app wiring, middleware (CORS, gzip), static `/app` mount.
- `app/config.py`: environment-backed settings.
- `app/collector.py`: AWN ingest loop, DB upserts, broadcast publish.
- `app/routes/history.py`: history and latest endpoints.
- `app/routes/stream.py`: SSE stream endpoint.
- `app/routes/astronomy.py`: astronomy cache/fallback logic.
- `app/schemas.py`: response contracts.

## Contracts To Preserve

- Latest endpoint payload is wrapper object:
  - `reading`
  - `statistics`
- Stream endpoint payload uses same wrapper object in SSE `reading` events.
- Metric day extremes are nested under each metric section in `statistics`.
- SSE periodic snapshot interval is configurable by `SSE_EMIT_INTERVAL_SECONDS`.
- Astronomy endpoint serves stale cache on upstream failure when available.

## Editing Guidance

- Keep payload shape backward-compatible unless explicitly requested.
- If you change schema/contracts:
  - update route docs and examples,
  - update `README.md`,
  - update `.env.example` if config changes.
- Never commit secrets or local env values.

## Minimal Validation

```bash
python -m compileall app main.py
```

For stream changes, verify both:

1. live broadcast event path,
2. periodic snapshot path.

## Ignore/Noise

- Keep `nul` ignored and untracked.
- Avoid committing editor-only changes unless explicitly requested.
