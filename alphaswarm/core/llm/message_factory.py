from typing import Any, Dict, Literal


class MessageFactory:
    """Helper factory for creating LLM messages, supporting Anthropic's ephemeral cache."""

    @classmethod
    def message(cls, role: Literal["system", "user", "assistant"], content: str, cache: bool = False) -> Dict[str, Any]:
        if not cache:
            return {"role": role, "content": content}
        return {"role": role, "content": [{"type": "text", "text": content, "cache_control": {"type": "ephemeral"}}]}

    @classmethod
    def system_message(cls, message: str, cache: bool = False) -> Dict[str, Any]:
        return cls.message(role="system", content=message, cache=cache)

    @classmethod
    def user_message(cls, message: str, cache: bool = False) -> Dict[str, Any]:
        return cls.message(role="user", content=message, cache=cache)

    @classmethod
    def assistant_message(cls, message: str, cache: bool = False) -> Dict[str, Any]:
        return cls.message(role="assistant", content=message, cache=cache)
