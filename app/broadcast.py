"""Simple async pub/sub broadcaster for SSE streaming."""

import asyncio
from collections.abc import AsyncGenerator


class Broadcaster:
    """Manages SSE subscribers and broadcasts new weather data to all of them."""

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    async def publish(self, data: dict) -> None:
        for queue in self._subscribers:
            try:
                queue.put_nowait(data)
            except asyncio.QueueFull:
                pass  # Drop data for slow consumers

    async def subscribe(self) -> AsyncGenerator[dict, None]:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.append(queue)
        try:
            while True:
                data = await queue.get()
                yield data
        finally:
            self._subscribers.remove(queue)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


# Singleton instance
broadcaster = Broadcaster()
