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
        message_generator: Callable[[], str],  # TODO: consider returning Optional[str] and not call agent with None
        response_handler: Callable[[str], None] = print,
        should_process: Callable[[str], bool] = lambda input_str: len(input_str) > 0,
        skip_message: Callable[[str], None] = lambda _: None,
        max_history: int = 1,
    ) -> None:
        """
        Initialize CronJobClient with conditional processing.

        Args:
            agent: The AlphaSwarmAgent instance
            client_id: Unique identifier for the client
            interval_seconds: Interval between message generation
            message_generator: Function that generates messages
            response_handler: Function to handle agent responses
            should_process: Function that decides if a message should be processed by agent
            skip_message: Function to handle skipped messages
            max_history: Maximum number of messages to keep in history
        """
        super().__init__(agent, client_id, max_history=max_history)
        self.interval_seconds = interval_seconds
        self.message_generator = message_generator
        self.should_process = should_process
        self.response_handler = response_handler
        self.skip_message = skip_message

    async def get_message(self) -> Context:
        await asyncio.sleep(self.interval_seconds)
        message = self.message_generator()

        # If message should not be processed, handle it and return a quit signal
        if not self.should_process(message):
            self.skip_message(message)
            return Context(context=None, message="quit")

        return Context(context=None, message=message)

    async def on_agent_response(self, ctx: Context, message: ChatMessage) -> None:
        self.response_handler(message.content)

    async def on_agent_error(self, ctx: Context, error: ChatMessage) -> None:
        self.response_handler(f"Error: {error.content}")

    async def on_start(self) -> None:
        self.response_handler(f"Cron Job {self.id} started")

    async def on_stop(self) -> None:
        self.response_handler(f"Cron Job {self.id} stopped")

    async def start(self) -> None:
        """Override start to continue after skipped messages"""
        if self._lock:
            raise RuntimeError("Client already started")
        await self.on_start()
        self._lock = asyncio.Lock()
        try:
            while True:
                context = await self.get_message()
                if context.message.lower() == "quit":
                    continue  # Continue instead of break to keep the cron job running
                await self._process_message(context)
                await asyncio.sleep(1)
        finally:
            await self.stop()
