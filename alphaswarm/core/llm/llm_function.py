from __future__ import annotations

from typing import Any, Dict, Generic, List, Literal, Optional, Sequence, Type, TypeVar

import instructor
import litellm
from pydantic import BaseModel

from .message import Message

T_Response = TypeVar("T_Response", bound=BaseModel)

litellm.modify_params = True  # for calls with system message only for anthropic


class LLMFunction(Generic[T_Response]):
    """
    A typed interface for LLM interactions that ensures structured Pydantic outputs.
    Build on top of litellm and instructor.
    """

    def __init__(
        self,
        model_id: str,
        response_model: Type[T_Response],
        system_message: Optional[str] = None,
        messages: Optional[Sequence[Message]] = None,
        max_retries: int = 3,
    ) -> None:
        """Initialize an LLMFunction instance.

        Args:
            model_id (str): LiteLLM model ID to use
            response_model (Type[BaseModel]): Pydantic model class for structuring responses
            system_message (Optional[str]): Optional system message
            messages (Optional[Sequence[Message]]): Optional sequence of pre-formatted messages
            max_retries (int): Maximum number of retry attempts

        Raises:
            ValueError: If both system_message and messages are not provided
        """
        self.model_id = model_id
        self.response_model = response_model
        self.max_retries = max_retries
        self.messages = self._validate_messages(system_message, messages, role="system")

        self.client = instructor.from_litellm(litellm.completion)

    @staticmethod
    def _validate_messages(
        str_message: Optional[str],
        messages: Optional[Sequence[Message]],
        role: Literal["system", "user"],
        allow_empty: bool = False,
    ) -> List[Message]:
        """Convert a string message and/or a list of messages to a proper list of messages.

        Args:
            str_message (Optional[str]): Optional string message to convert
            messages (Optional[Sequence[Message]]): Optional sequence of pre-formatted messages
            role (Literal["system", "user"]): The role for the string message
            allow_empty (bool): Whether to allow returning an empty list when no messages are provided

        Returns:
            List of validated messages in the correct format

        Raises:
            ValueError: If no messages are provided and allow_empty is False
        """
        if str_message is None and messages is None:
            if allow_empty:
                return []
            raise ValueError("At least one of str message, messages is required")

        llm_messages: List[Message] = []
        if str_message is not None:
            llm_messages.append(Message(role=role, content=str_message))
        if messages is not None:
            llm_messages.extend(messages)

        return llm_messages

    def execute(
        self,
        user_message: Optional[str] = None,
        messages: Optional[Sequence[Message]] = None,
        **kwargs: Any,
    ) -> T_Response:
        """Execute the LLM function with the given messages.

        Args:
            user_message (Optional[str]): Optional string message from the user
            messages (Optional[Sequence[Message]]): Optional sequence of pre-formatted messages
            **kwargs: Additional keyword arguments to pass to the LLM client

        Returns:
            A structured response matching the provided response_model type
        """
        llm_messages = self.messages + self._validate_messages(user_message, messages, role="user", allow_empty=True)
        llm_messages_dicts: List[Dict[str, Any]] = [message.to_dict() for message in llm_messages]

        return self.client.create(
            model=self.model_id,
            response_model=self.response_model,
            messages=llm_messages_dicts,
            max_retries=self.max_retries,
            **kwargs,
        )


class LLMFunctionFromPromptFiles(LLMFunction[T_Response]):
    """
    Extends LLMFunction to support prompt templates loaded from files, with an ability to format them with parameters.
    """

    def __init__(
        self,
        model_id: str,
        response_model: Type[T_Response],
        system_prompt_path: str,
        user_prompt_path: Optional[str] = None,
        system_prompt_params: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> None:
        """Initialize an LLMFunctionFromPromptFiles instance.

        Args:
            model_id (str): LiteLLM model ID to use
            response_model (Type[BaseModel]): Pydantic model class for structuring responses
            system_prompt_path (str): Path to the file containing the system prompt template
            user_prompt_path (Optional[str]): Optional path to the file containing the user prompt template
            system_prompt_params (Optional[Dict[str, Any]]): Optional parameters to format the system prompt template
            max_retries (int): Maximum number of retry attempts
        """
        with open(system_prompt_path, "r", encoding="utf-8") as f:
            system_prompt_template = f.read()

        system_prompt = self._format(system_prompt_template, system_prompt_params)

        self.user_prompt_template: Optional[str] = None
        if user_prompt_path is not None:
            with open(user_prompt_path, "r", encoding="utf-8") as f:
                self.user_prompt_template = f.read()

        super().__init__(
            model_id=model_id,
            response_model=response_model,
            system_message=system_prompt,
            max_retries=max_retries,
        )

    def execute(
        self,
        user_message: Optional[str] = None,
        messages: Optional[Sequence[Message]] = None,
        user_prompt_params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> T_Response:
        """Execute the LLM function using the loaded prompt templates.

        Args:
            user_message (Optional[str]): Must be None - direct messages not supported
            messages (Optional[Sequence[Message]]): Must be None - direct messages not supported
            user_prompt_params (Optional[Dict[str, Any]]): Optional parameters to format the user prompt template
            **kwargs: Additional keyword arguments to pass to the LLM client

        Returns:
            A structured response matching the provided response_model type

        Raises:
            ValueError: If user_message/messages are provided or
                if user_prompt_params are provided without a user prompt template
        """
        if user_message is not None or messages is not None:
            raise ValueError(
                "Both `user_message` and `messages` are expected to be None for LLMFunctionFromPromptFiles.execute "
                "since they are ignored"
            )

        if self.user_prompt_template is None:
            if user_prompt_params is not None:
                raise ValueError("User prompt params provided but no user prompt template exists")
            return super().execute(**kwargs)

        user_prompt = self._format(self.user_prompt_template, user_prompt_params)
        return super().execute(user_message=user_prompt, **kwargs)

    @staticmethod
    def _format(template: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Format the template with the given parameters."""
        return template.format(**params) if params is not None else template
