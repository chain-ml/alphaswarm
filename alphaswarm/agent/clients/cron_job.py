import asyncio
from typing import Any, Callable

from ..agent import AlphaSwarmAgentManager


class CronJobClient:
    def __init__(
        self,
        manager: AlphaSwarmAgentManager,
        client_id: str,
        interval_seconds: int,
        message_generator: Callable[[], str],
        response_handler: Callable[[str], Any] = print,
    ):
        self.client_id = client_id
        self._manager = manager
        self.interval_seconds = interval_seconds
        self.message_generator = message_generator
        self.response_handler = response_handler
        self._running = False

    async def start(self):
        self._running = True
        try:
            while self._running:
                message = self.message_generator()
                response = await self._manager.handle_message(self.client_id, message)
                self.response_handler(response)
                await asyncio.sleep(self.interval_seconds)
        finally:
            await self._manager.unregister_client(self.client_id)

    async def stop(self):
        self._running = False
