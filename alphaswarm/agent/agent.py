import asyncio
import os
import yaml
from typing import Optional, Sequence
import pydantic

from smolagents import CODE_SYSTEM_PROMPT, CodeAgent, LiteLLMModel, Tool

from alphaswarm.config import BASE_PATH
from alphaswarm.strategy.schema import Strategy


class AlphaSwarmAgent:

    def __init__(self, tools: Sequence[Tool], *, model_id: str, hints: Optional[str] = None) -> None:

        system_prompt = CODE_SYSTEM_PROMPT + "\n" + hints if hints else None
        self._wallet_address = os.getenv("BASE_WALLET_ADDRESS")
        self._agent = CodeAgent(
            tools=list(tools),
            model=LiteLLMModel(model_id=model_id),
            system_prompt=system_prompt,
        )
        self._strategy_config = self._load_and_validate_strategy_config()

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
            "# Strategy",
            str(self._strategy_config.model_dump(mode='json')),
            "",
            "# Messages",
            current_message,
            "",
        ]

        return "\n".join(messages)
    

    def _load_and_validate_strategy_config(self) -> Strategy:
        # TODO: place strategy yaml in appropriate directory
        strategy_path = os.path.join(BASE_PATH, "alphaswarm", "strategy", "strategy_config.yaml")
        try:
            with open(strategy_path, "r", encoding="utf-8") as f:
                strategy_dict = yaml.safe_load(f)
                strategy = Strategy.model_validate(strategy_dict)
                return strategy
        except FileNotFoundError:
            raise Exception("No trading strategy exists. Please configure a strategy before editing.")
        except pydantic.ValidationError as e:
            raise Exception(f"Invalid strategy configuration: {str(e)}")
