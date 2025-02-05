import asyncio
import os
from typing import Optional, Sequence

from alphaswarm.tools.strategy_analysis.strategy import Strategy
from smolagents import CODE_SYSTEM_PROMPT, CodeAgent, LiteLLMModel, Tool


class AlphaSwarmAgent:

    def __init__(
        self,
        tools: Sequence[Tool],
        strategy: Strategy,
        system_prompt: Optional[str] = None,
        hints: Optional[str] = None,
    ) -> None:

        system_prompt = system_prompt or CODE_SYSTEM_PROMPT
        system_prompt = system_prompt + "\n" + hints if hints else system_prompt

        self._wallet_address = os.getenv("BASE_WALLET_ADDRESS")
        self._strategy_rules = strategy.rules
        self._agent = CodeAgent(
            tools=list(tools),
            model=LiteLLMModel(model_id=strategy.model_id),
            system_prompt=system_prompt,
            additional_authorized_imports=["json", "decimal"],
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
            "## Strategy Rules\n\n```",
            self._strategy_rules,
            "\n\n```\n",
            "",
            "## Messages",
            current_message,
            "",
        ]

        return "\n".join(messages)
