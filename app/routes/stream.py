import asyncio
import json
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.broadcast import broadcaster
from app.config import settings
from app.converter import strip_sensitive_fields
from app.statistics import get_reading_statistics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stream", tags=["stream"])


@router.get(
    "",
    summary="Stream readings in real-time",
    description="Server-Sent Events (SSE) endpoint that pushes new weather readings as they "
    "are collected. Each event has type `reading` and contains a JSON "
    "payload with the latest reading plus aggregate station statistics. "
    "Connect with `EventSource` in the browser or any SSE client.\n\n"
    "**Event format:**\n"
    "```\n"
    "event: reading\n"
    "data: {\"reading\": {\"temp_c\": 19.11, ...}, \"statistics\": {...}}\n"
    "```",
    responses={
        200: {
            "description": "SSE event stream of weather readings",
            "content": {"text/event-stream": {}},
        }
    },
)
async def stream_readings():
    """SSE endpoint that streams new weather readings in real-time."""

    async def event_generator():
        logger.info("New SSE subscriber connected")
        subscription = None
        next_item_task = None
        try:
            subscription = broadcaster.subscribe()
            # Keep one pending __anext__ task and poll it with timeout for keepalives.
            # Important: do NOT cancel __anext__ on timeout, or the async generator closes.
            next_item_task = asyncio.create_task(subscription.__anext__())

            while True:
                done, _ = await asyncio.wait({next_item_task}, timeout=30)
                if not done:
                    # No message received in 30 seconds, send keepalive to keep connection alive
                    logger.debug("Sending keepalive to SSE client")
                    yield b": keepalive\n\n"
                    continue

                try:
                    data = next_item_task.result()
                except StopAsyncIteration:
                    logger.info("SSE subscription completed")
                    break

                # Schedule the next message before processing so the stream keeps flowing.
                next_item_task = asyncio.create_task(subscription.__anext__())

                if isinstance(data, dict) and "reading" in data and "statistics" in data:
                    reading_payload = data.get("reading")
                    payload = {
                        "reading": (
                            strip_sensitive_fields(reading_payload)
                            if isinstance(reading_payload, dict)
                            else {}
                        ),
                        "statistics": data.get("statistics"),
                    }
                else:
                    reading_payload = strip_sensitive_fields(data) if isinstance(data, dict) else {}
                    statistics = await get_reading_statistics(settings.awn_mac_address)
                    payload = {
                        "reading": reading_payload,
                        "statistics": statistics.model_dump(mode="json"),
                    }

                json_data = json.dumps(payload, default=str)
                event = f"event: reading\ndata: {json_data}\n\n"
                yield event.encode("utf-8")
        except asyncio.CancelledError:
            logger.info("SSE stream cancelled")
        except Exception as exc:
            logger.error("SSE stream error: %s", exc)
        finally:
            if next_item_task is not None and not next_item_task.done():
                next_item_task.cancel()
                try:
                    await next_item_task
                except Exception:
                    pass
            if subscription is not None:
                await subscription.aclose()
            logger.info("SSE subscriber disconnected")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
