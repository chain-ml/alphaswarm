from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any, Dict, Generic, List, Literal, Optional, Sequence, Type, TypeVar

import instructor
import litellm
from litellm.types.utils import ModelResponse
from pydantic import BaseModel

from .message import Message

litellm.modify_params = True  # for calls with system message only for anthropic

T_Response = TypeVar("T_Response", bound=BaseModel)


@dataclass
class LLMFunctionResponse(Generic[T_Response]):
    """
    A response from the LLM function, containing parsed response and litellm completion object.
    """

    response: T_Response
    completion: ModelResponse


class LLMFunctionBase(Generic[T_Response], abc.ABC):
    """
    Base class for LLM function - a typed interface for LLM interactions that ensures structured Pydantic outputs.
    Build on top of litellm and instructor.
    """

    def __init__(self, model_id: str, response_model: Type[T_Response], max_retries: int = 3) -> None:
        """Initialize the LLM function instance.

        Args:
            model_id (str): LiteLLM model ID to use
            response_model (Type[BaseModel]): Pydantic model class for structuring responses
            max_retries (int): Maximum number of retry attempts
        """
        self.model_id = model_id
        self.response_model = response_model
        self.max_retries = max_retries

        self.client = instructor.from_litellm(litellm.completion)

    def execute(self, *args: Any, **kwargs: Any) -> T_Response:
        """
        Execute the LLM function and return the response.

        Returns:
            A structured response matching the provided response_model type
        """
        llm_func_response = self.execute_with_completion(*args, **kwargs)
        return llm_func_response.response

    @abc.abstractmethod
    def execute_with_completion(self, *args: Any, **kwargs: Any) -> LLMFunctionResponse[T_Response]:
        """
        Execute the LLM function and return both response and completion.
        Each implementation defines its own interface.

        Returns:
            A structured response matching the provided response_model type and the completion object
        """
        pass

    def _execute_with_completion(self, messages: Sequence[Message], **kwargs: Any) -> LLMFunctionResponse[T_Response]:
        """Internal core execution method used by all derived classes."""
        messages_dicts = [message.to_dict() for message in messages]
        response, completion = self.client.create_with_completion(
            model=self.model_id,
            response_model=self.response_model,
            messages=messages_dicts,
            max_retries=self.max_retries,
            **kwargs,
        )
        return LLMFunctionResponse(response=response, completion=completion)


class LLMFunction(LLMFunctionBase[T_Response]):
    """LLM function with interface for both string messages and Message objects."""

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
        super().__init__(model_id=model_id, response_model=response_model, max_retries=max_retries)
        self.starter_messages = self._validate_messages(system_message, messages, role="system", allow_empty=False)

    def execute_with_completion(
        self, user_message: Optional[str] = None, messages: Optional[Sequence[Message]] = None, **kwargs: Any
    ) -> LLMFunctionResponse[T_Response]:
        """Execute the LLM function with the given messages.

        Args:
            user_message (Optional[str]): Optional string message from the user
            messages (Optional[Sequence[Message]]): Optional sequence of pre-formatted messages
            **kwargs: Additional keyword arguments to pass to the LLM client

        Returns:
            A structured response matching the provided response_model type and the completion object
        """
        all_messages = self.starter_messages + self._validate_messages(
            user_message, messages, role="user", allow_empty=True
        )
        return super()._execute_with_completion(messages=all_messages, **kwargs)

    @staticmethod
    def _validate_messages(
        str_message: Optional[str],
        messages: Optional[Sequence[Message]],
        role: Literal["system", "user"],
        allow_empty: bool,
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

        all_messages: List[Message] = []
        if str_message is not None:
            all_messages.append(Message.create(role=role, content=str_message))
        if messages is not None:
            all_messages.extend(messages)
        return all_messages


class LLMFunctionTemplated(LLMFunctionBase[T_Response]):
    """LLM function supporting prompt templates with parameter formatting."""

    def __init__(
        self,
        model_id: str,
        response_model: Type[T_Response],
        system_prompt_template: str,
        user_prompt_template: Optional[str] = None,
        system_prompt_params: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> None:
        """Initialize an LLMFunctionTemplated instance.

        Args:
            model_id (str): LiteLLM model ID to use
            response_model (Type[BaseModel]): Pydantic model class for structuring responses
            system_prompt_template (str): Template for the system message
            user_prompt_template (Optional[str]): Template for the user message
            system_prompt_params (Optional[Dict[str, Any]]): Parameters for formatting the system prompt
            max_retries (int): Maximum number of retry attempts
        """
        super().__init__(model_id=model_id, response_model=response_model, max_retries=max_retries)
        self.system_prompt_template = system_prompt_template
        self.system_prompt = self._format(system_prompt_template, system_prompt_params)
        self.user_prompt_template = user_prompt_template

    def execute_with_completion(
        self,
        user_prompt_params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> LLMFunctionResponse[T_Response]:
        """Execute the LLM function using the loaded prompt templates.

        Args:
            user_prompt_params (Optional[Dict[str, Any]]): Optional parameters to format the user prompt template
            **kwargs: Additional keyword arguments to pass to the LLM client

        Returns:
            A structured response matching the provided response_model type and the completion object

        Raises:
            ValueError: If user_prompt_params are provided without a user prompt template
        """
        messages: List[Message] = [Message.system(self.system_prompt)]

        if self.user_prompt_template is None:
            if user_prompt_params is not None:
                raise ValueError("User prompt params provided but no user prompt template exists")
            return self._execute_with_completion(messages=messages, **kwargs)

        user_prompt = self._format(self.user_prompt_template, user_prompt_params)
        messages.append(Message.user(user_prompt))
        return self._execute_with_completion(messages=messages, **kwargs)

    @classmethod
    def from_files(
        cls,
        model_id: str,
        response_model: Type[T_Response],
        system_prompt_path: str,
        user_prompt_path: Optional[str] = None,
        system_prompt_params: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> LLMFunctionTemplated[T_Response]:
        """Create an instance from template files.

        Args:
            model_id (str): LiteLLM model ID to use
            response_model (Type[BaseModel]): Pydantic model class for structuring responses
            system_prompt_path (str): Path to the system prompt template file
            user_prompt_path (Optional[str]): Path to the user prompt template file
            system_prompt_params (Optional[Dict[str, Any]]): Parameters for formatting the system prompt
            max_retries (int): Maximum number of retry attempts
        """
        with open(system_prompt_path, "r", encoding="utf-8") as f:
            system_prompt_template = f.read()

        user_prompt_template: Optional[str] = None
        if user_prompt_path:
            with open(user_prompt_path, "r", encoding="utf-8") as f:
                user_prompt_template = f.read()

        return cls(
            model_id=model_id,
            response_model=response_model,
            system_prompt_template=system_prompt_template,
            user_prompt_template=user_prompt_template,
            system_prompt_params=system_prompt_params,
            max_retries=max_retries,
        )

    @staticmethod
    def _format(template: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Format the template string with the given optional parameters."""
        return template.format(**params) if params is not None else template
