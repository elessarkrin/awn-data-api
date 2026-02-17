import asyncio
import json
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.broadcast import broadcaster
from app.config import settings
from app.converter import strip_sensitive_fields
from app.database import DailyReading, async_session
from app.statistics import get_reading_statistics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stream", tags=["stream"])


def _encode_event(payload: dict) -> bytes:
    json_data = json.dumps(payload, default=str)
    return f"event: reading\ndata: {json_data}\n\n".encode("utf-8")


async def _build_snapshot_payload(mac_address: str) -> dict:
    async with async_session() as session:
        result = await session.execute(
            select(DailyReading)
            .where(DailyReading.mac_address == mac_address)
            .order_by(DailyReading.timestamp.desc())
            .limit(1)
        )
        latest = result.scalar_one_or_none()

    reading_payload = {}
    if latest is not None and isinstance(latest.data, dict):
        reading_payload = strip_sensitive_fields(latest.data)

    statistics = await get_reading_statistics(mac_address)
    return {
        "reading": reading_payload,
        "statistics": statistics.model_dump(mode="json"),
    }


async def _normalize_payload(data: object, mac_address: str) -> dict:
    if isinstance(data, dict) and "reading" in data and "statistics" in data:
        reading_payload = data.get("reading")
        return {
            "reading": (
                strip_sensitive_fields(reading_payload)
                if isinstance(reading_payload, dict)
                else {}
            ),
            "statistics": data.get("statistics"),
        }

    reading_payload = strip_sensitive_fields(data) if isinstance(data, dict) else {}
    statistics = await get_reading_statistics(mac_address)
    return {
        "reading": reading_payload,
        "statistics": statistics.model_dump(mode="json"),
    }


@router.get(
    "",
    summary="Stream readings in real-time",
    description="Server-Sent Events (SSE) endpoint that pushes new weather readings as they "
    "are collected. Each event has type `reading` and contains a JSON "
    "payload with the latest reading plus aggregate station statistics. "
    "On connection, it sends an immediate snapshot. In addition to live updates, "
    "the stream emits a snapshot every `SSE_EMIT_INTERVAL_SECONDS` (default 60). "
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
        emit_interval = max(1, settings.sse_emit_interval_seconds)
        try:
            subscription = broadcaster.subscribe()
            # Keep one pending __anext__ task and poll it with timeout.
            # Important: do NOT cancel __anext__ on timeout, or the async generator closes.
            next_item_task = asyncio.create_task(subscription.__anext__())
            # Send one snapshot immediately on connect.
            initial_payload = await _build_snapshot_payload(settings.awn_mac_address)
            yield _encode_event(initial_payload)

            while True:
                done, _ = await asyncio.wait({next_item_task}, timeout=emit_interval)
                if not done:
                    payload = await _build_snapshot_payload(settings.awn_mac_address)
                    yield _encode_event(payload)
                    continue

                try:
                    data = next_item_task.result()
                except StopAsyncIteration:
                    logger.info("SSE subscription completed")
                    break

                # Schedule the next message before processing so the stream keeps flowing.
                next_item_task = asyncio.create_task(subscription.__anext__())
                payload = await _normalize_payload(data, settings.awn_mac_address)
                yield _encode_event(payload)
        except asyncio.CancelledError:
            logger.info("SSE stream cancelled")
        except Exception as exc:
            logger.error("SSE stream error: %s", exc)
        finally:
            if next_item_task is not None and not next_item_task.done():
                next_item_task.cancel()
                try:
                    await next_item_task
                except asyncio.CancelledError:
                    pass
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
