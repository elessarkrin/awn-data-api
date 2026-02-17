#!/usr/bin/env sh
set -eu

cd "${APP_DIR:-/app}"

if [ "${RUN_BACKFILL_BEFORE_START:-1}" = "1" ]; then
  echo "[entrypoint] Running backfill: ${BACKFILL_CMD:-python backfill.py}"
  if ! sh -c "${BACKFILL_CMD:-python backfill.py}"; then
    if [ "${BACKFILL_STRICT:-0}" = "1" ]; then
      echo "[entrypoint] Backfill failed and BACKFILL_STRICT=1; exiting." >&2
      exit 1
    fi
    echo "[entrypoint] Backfill failed; continuing (BACKFILL_STRICT=0)." >&2
  fi
else
  echo "[entrypoint] Backfill disabled (RUN_BACKFILL_BEFORE_START=${RUN_BACKFILL_BEFORE_START:-1})."
fi

if [ -n "${PRE_START_CMD:-}" ]; then
  echo "[entrypoint] Running PRE_START_CMD"
  sh -c "${PRE_START_CMD}"
fi

if [ "$#" -gt 0 ]; then
  echo "[entrypoint] Executing custom command: $*"
  exec "$@"
fi

UVICORN_CMD="uvicorn ${UVICORN_APP:-main:app} --host ${UVICORN_HOST:-0.0.0.0} --port ${UVICORN_PORT:-8000} --workers ${UVICORN_WORKERS:-1} --log-level ${UVICORN_LOG_LEVEL:-info}"

if [ "${UVICORN_RELOAD:-0}" = "1" ]; then
  UVICORN_CMD="${UVICORN_CMD} --reload"
fi

if [ -n "${UVICORN_EXTRA_ARGS:-}" ]; then
  UVICORN_CMD="${UVICORN_CMD} ${UVICORN_EXTRA_ARGS}"
fi

echo "[entrypoint] Starting server: ${UVICORN_CMD}"
exec sh -c "${UVICORN_CMD}"
