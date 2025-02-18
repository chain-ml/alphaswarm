import asyncio
from datetime import datetime
from typing import Optional, Sequence

from alphaswarm.core.tool import AlphaSwarmTool, AlphaSwarmToSmolAgentsToolAdapter
from smolagents import CODE_SYSTEM_PROMPT, CodeAgent, LiteLLMModel


class AlphaSwarmAgent:

    def __init__(
        self,
        tools: Sequence[AlphaSwarmTool],
        model_id: str = "anthropic/claude-3-5-sonnet-20241022",
        system_prompt: Optional[str] = None,
        hints: Optional[str] = None,
    ) -> None:
        """
        Initialize the AlphaSwarmAgent.

        Args:
            tools: A sequence of tools to use.
            model_id: The LiteLLM model ID of the LLM to use.
            system_prompt: Optional system prompt to use. If not provided, the default system prompt will be used.
            hints: Optional additional hints to provide to the agent.
        """

        system_prompt = system_prompt or CODE_SYSTEM_PROMPT
        system_prompt = system_prompt + "\n" + hints if hints else system_prompt

        self._agent = CodeAgent(
            tools=[AlphaSwarmToSmolAgentsToolAdapter.adapt(tool) for tool in tools],
            model=LiteLLMModel(model_id=model_id),
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
            "",
            "## Current Date and Time",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "",
            "## Messages",
            current_message,
            "",
        ]

        return "\n".join(messages)
