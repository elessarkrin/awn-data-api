"""Standalone script to backfill historical weather data from the AWN API.

Run anytime to fill gaps in the database:
    python backfill.py
"""

import asyncio
import logging

from app.collector import backfill_history
from app.config import settings
from app.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> int:
    if not (settings.awn_api_key and settings.awn_application_key):
        logger.error("AWN credentials not configured - set AWN_API_KEY and AWN_APPLICATION_KEY")
        return 1

    await init_db()
    total = await backfill_history(settings.awn_mac_address)
    logger.info("Done - %d readings upserted", total)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
