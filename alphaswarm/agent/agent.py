import asyncio
import os
from typing import Optional, Sequence

from smolagents import CodeAgent, LiteLLMModel, Tool, CODE_SYSTEM_PROMPT


class AlphaSwarmAgent:

    def __init__(self, tools: Sequence[Tool], *, model_id: str, hints: Optional[str] = None) -> None:

        system_prompt = CODE_SYSTEM_PROMPT + "\n" + hints if hints else None
        self._wallet_address = os.getenv("BASE_WALLET_ADDRESS")
        self._agent = CodeAgent(
            tools=list(tools),
            model=LiteLLMModel(model_id=model_id),
            system_prompt=system_prompt,
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
            "# Base Wallet Address",
            str(self._wallet_address),
            "",
            "# Messages",
            current_message,
            "",
        ]

        return "\n".join(messages)
