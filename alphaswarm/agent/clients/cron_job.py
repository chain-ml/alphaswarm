import asyncio
from typing import Any, Callable

from ..agent import AlphaSwarmAgent
from ..agent_client import AlphaSwarmAgentClient, ChatMessage, Context


class CronJobClient(AlphaSwarmAgentClient[Any]):

    def __init__(
        self,
        agent: AlphaSwarmAgent,
        client_id: str,
        interval_seconds: int,
        message_generator: Callable[[], str],
        response_handler: Callable[[str], None] = print,
    ) -> None:
        super().__init__(agent, client_id)
        self.interval_seconds = interval_seconds
        self.message_generator = message_generator
        self.response_handler = response_handler

    async def get_message(self) -> Context:
        await asyncio.sleep(self.interval_seconds)
        message = self.message_generator()
        return Context(context=None, message=message)

    async def on_agent_response(self, ctx: Context, message: ChatMessage) -> None:
        self.response_handler(message.content)

    async def on_agent_error(self, ctx: Context, error: ChatMessage) -> None:
        self.response_handler(f"Error: {error.content}")

    async def on_start(self) -> None:
        self.response_handler(f"Cron Job {self.id} started")

    async def on_stop(self) -> None:
        self.response_handler(f"Cron Job {self.id} stopped")
