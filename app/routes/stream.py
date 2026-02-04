import json
import logging

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.broadcast import broadcaster

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stream", tags=["stream"])


@router.get("")
async def stream_readings():
    """SSE endpoint that streams new weather readings in real-time.

    Clients connect to this endpoint and receive `data` events
    whenever a new reading is collected from the weather station.
    """

    async def event_generator():
        async for data in broadcaster.subscribe():
            yield {
                "event": "reading",
                "data": json.dumps(data, default=str),
            }

    return EventSourceResponse(event_generator())
