# syntax=docker/dockerfile:1.7
ARG PYTHON_IMAGE=python:3.13-slim
FROM ${PYTHON_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_DIR=/app \
    DATA_DIR=/data \
    DATABASE_URL=sqlite+aiosqlite:////data/weather.db \
    RUN_BACKFILL_BEFORE_START=1 \
    BACKFILL_STRICT=0 \
    BACKFILL_CMD="python backfill.py" \
    PRE_START_CMD="" \
    UVICORN_APP=main:app \
    UVICORN_HOST=0.0.0.0 \
    UVICORN_PORT=8000 \
    UVICORN_WORKERS=1 \
    UVICORN_LOG_LEVEL=info \
    UVICORN_RELOAD=0 \
    UVICORN_EXTRA_ARGS=""

WORKDIR ${APP_DIR}

RUN apt-get update \
    && apt-get install -y --no-install-recommends tini \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . ${APP_DIR}
COPY docker/entrypoint.sh /entrypoint.sh

RUN mkdir -p ${DATA_DIR} \
    && chmod +x /entrypoint.sh

EXPOSE 8000
VOLUME ["/data"]

ENTRYPOINT ["tini", "--", "/entrypoint.sh"]
