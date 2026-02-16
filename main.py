import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
from starlette.types import Scope

from app.collector import collection_loop
from app.config import settings
from app.database import init_db
from app.routes import astronomy, history, stream

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class SPAStaticFiles(StaticFiles):
    """Serve a single-page app build with index.html fallback for client routes."""

    async def check_config(self) -> None:
        # Allow booting without a UI build present yet.
        self.config_checked = True

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404 and "." not in path:
                return await super().get_response("index.html", scope)
            raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    logger.info("Database initialized")

    # Start the collector (runs in parallel â€” SSE subscribers get live data right away)
    collector_task = asyncio.create_task(collection_loop())
    logger.info("Data collector started")

    yield

    # Shutdown
    collector_task.cancel()
    try:
        await collector_task
    except asyncio.CancelledError:
        pass

    logger.info("Data collector stopped")


app = FastAPI(
    title="AWN Data API",
    description=(
        "REST API for collecting and querying Ambient Weather Network station data.\n\n"
        "The service polls the AWN REST API every 60 seconds, converts all measurements "
        "from imperial to metric units, and stores them in a local database with a "
        "configurable retention period (default 365 days). On startup, the service "
        "backfills up to one year of historical data from the AWN API.\n\n"
        "## Endpoints\n\n"
        "- **History** â€” query stored readings with pagination and date filtering\n"
        "- **Stream** â€” subscribe to real-time readings via Server-Sent Events\n"
        "- **Astronomy** â€” sun/moon data refreshed every 5 minutes (on the clock)\n"
        "- **Health** â€” service health check\n\n"
        "## Units\n\n"
        "All values are converted at ingestion:\n"
        "temperature â†’ Â°C, wind â†’ km/h, pressure â†’ mmHg, rainfall â†’ mm.\n"
        "See `/api/history/fields` for the full field reference."
    ),
    version="0.1.0",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "history",
            "description": "Query historical weather readings with pagination and date range filtering.",
        },
        {
            "name": "stream",
            "description": "Real-time weather data via Server-Sent Events (SSE).",
        },
        {
            "name": "astronomy",
            "description": "Sun and moon positions, phases, and twilight times.",
        },
        {
            "name": "health",
            "description": "Service health and readiness checks.",
        },
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(history.router, prefix="/api")
app.include_router(stream.router, prefix="/api")
app.include_router(astronomy.router, prefix="/api")
app.mount(
    "/app",
    SPAStaticFiles(directory=settings.react_build_dir, html=True, check_dir=False),
    name="react-app",
)


@app.get(
    "/health",
    tags=["health"],
    summary="Health check",
    description="Returns the service status. Use this to verify the API is running and responsive.",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {"status": "ok"}
                }
            },
        }
    },
)
async def health():
    """Check service health."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

