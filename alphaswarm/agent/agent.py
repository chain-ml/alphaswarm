import asyncio
import os
from typing import Optional, Sequence

from smolagents import CodeAgent, LiteLLMModel, Tool


class AlphaSwarmAgent:

    def __init__(self, tools: Sequence[Tool], *, model_id: str, system_prompt: str) -> None:
        self._wallet_address = os.getenv("BASE_WALLET_ADDRESS")
        self._agent = CodeAgent(
            tools=list(tools),
            model=LiteLLMModel(model_id=model_id),
            additional_authorized_imports=[],
            system_prompt=system_prompt,
        )

    async def process_message(
        self,
        current_message: str,
        send_notifications: bool = False,
    ) -> Optional[str]:
        """
        Process a message and return a response.

        Args:
            current_message: The current message to process
            send_notifications: Whether to send notifications for signals
        Returns:
            Response string, or None if processing failed
        """
        try:
            context = self._build_context(current_message, send_notifications)

            # Run the agent in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._agent.run, context)
            return str(result)

        except Exception as e:
            return f"Sorry, I encountered an error: {str(e)}"

    def _build_context(self, current_message: str, send_notifications: bool = False) -> str:
        messages = [
            "# Base Wallet Address",
            str(self._wallet_address),
            "",
            "# Messages",
            current_message,
            "",
        ]

        if "analyze" in current_message.lower():
            messages.append(f"\nsend_notifications: {send_notifications}")

        return "\n".join(messages)
