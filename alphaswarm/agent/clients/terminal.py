import asyncio
from typing import Any

from ..agent import AlphaSwarmAgent
from ..agent_client import AlphaSwarmAgentClient, ChatMessage, Context


class TerminalClient(AlphaSwarmAgentClient[Any]):

    def __init__(self, client_id: str, agent: AlphaSwarmAgent):
        super().__init__(agent, client_id)
        self._client_id = client_id

    async def on_agent_response(self, ctx: Context, message: ChatMessage) -> None:
        token_counts = self._agent._agent.monitor.get_total_token_counts()
        print(f"Total input tokens: {token_counts['input']}")
        print(f"Total output tokens: {token_counts['output']}")
        print(f"Total tokens used: {token_counts['input'] + token_counts['output']}")
        print("\n\n")
        print(f"Response: {message.content}")

    async def on_agent_error(self, ctx: Context, error: ChatMessage) -> None:
        print(f"Error: {error.content}")

    async def on_stop(self) -> None:
        print("Bye")

    async def on_start(self) -> None:
        print("Hello there!")

    async def get_message(self) -> Context:
        message = await asyncio.get_event_loop().run_in_executor(None, input, f"🤖 {self._client_id}> ")
        return Context(context=None, message=message)
