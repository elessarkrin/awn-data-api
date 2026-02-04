import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.collector import collection_loop
from app.config import settings
from app.database import init_db
from app.routes import daily, monthly, stream, yearly

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    logger.info("Database initialized")

    collector_task = None
    if settings.awn_api_key and settings.awn_mac_address:
        collector_task = asyncio.create_task(collection_loop())
        logger.info("Data collector started")
    else:
        logger.warning(
            "AWN credentials not configured — collector disabled. "
            "Set AWN_API_KEY, AWN_APPLICATION_KEY, and AWN_MAC_ADDRESS in .env"
        )

    yield

    # Shutdown
    if collector_task:
        collector_task.cancel()
        try:
            await collector_task
        except asyncio.CancelledError:
            pass
        logger.info("Data collector stopped")


app = FastAPI(
    title="AWN Data API",
    description="Ambient Weather Network data collection and query service",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(daily.router, prefix="/api")
app.include_router(monthly.router, prefix="/api")
app.include_router(yearly.router, prefix="/api")
app.include_router(stream.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
