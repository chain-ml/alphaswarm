import asyncio
import os
from collections import defaultdict
from typing import Dict, Optional, Sequence

from alphaswarm.utils import load_strategy_config
from smolagents import CODE_SYSTEM_PROMPT, CodeAgent, LiteLLMModel, Tool


class AlphaSwarmAgent:

    def __init__(self, tools: Sequence[Tool], *, model_id: str, hints: Optional[str] = None) -> None:

        system_prompt = CODE_SYSTEM_PROMPT + "\n" + hints if hints else None
        self._wallet_address = os.getenv("BASE_WALLET_ADDRESS")
        self._agent = CodeAgent(
            tools=list(tools),
            model=LiteLLMModel(model_id=model_id),
            system_prompt=system_prompt,
            additional_authorized_imports=["json"],
        )

    async def process_message(self, current_message: str) -> Optional[str]:
        """
        Process a message and return a response.

        Args:
            current_message: The current message to process
        Returns:
            Response string, or None if processing failed
        """
        try:
            context = self._build_context(current_message)

            # Run the agent in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._agent.run, context)
            return str(result)

        except Exception as e:
            return f"Sorry, I encountered an error: {str(e)}"

    def _build_context(self, current_message: str) -> str:
        messages = [
            "# User Context",
            "## Base Wallet Address",
            str(self._wallet_address),
            "",
            "## Strategy Config\n\n```strategy_config```\n\n",  # To be replaced by a user context management solution
            load_strategy_config(),
            "\n\n```\n",
            "",
            "## Messages",
            current_message,
            "",
        ]

        return "\n".join(messages)


class AlphaSwarmAgentManager:
    def __init__(self, agent: AlphaSwarmAgent):
        self._agent = agent
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._agent_lock = asyncio.Lock()

    async def register_client(self, client_id: str):
        """Register a new client connection"""
        self._locks[client_id] = asyncio.Lock()

    async def unregister_client(self, client_id: str):
        """Unregister a client and cleanup its resources"""
        if client_id in self._locks:
            del self._locks[client_id]

    async def handle_message(self, client_id: str, message: str) -> str:
        """Handle a message from a specific client"""
        async with self._locks[client_id], self._agent_lock:
            try:
                response = await self._agent.process_message(message)
                return response if response else "No response"
            except Exception as e:
                return f"Error processing message: {str(e)}"
