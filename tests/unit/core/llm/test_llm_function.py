import pytest

from alphaswarm.core.llm import LLMFunction, Message


def test_validate_messages_str_only() -> None:
    messages = LLMFunction._validate_messages(
        str_message="test message", messages=None, role="system", allow_empty=False
    )

    assert isinstance(messages, list)
    assert len(messages) == 1
    assert messages[0].role == "system"
    assert messages[0].content[0].type == "text"
    assert messages[0].content[0].text == "test message"


def test_validate_messages_list_only() -> None:
    test_messages = [
        Message.create(role="system", content="message 1"),
        Message.create(role="user", content="message 2"),
    ]
    messages = LLMFunction._validate_messages(
        str_message=None, messages=test_messages, role="system", allow_empty=False
    )

    assert messages == test_messages


def test_validate_messages_both() -> None:
    test_messages = [Message.create(role="system", content="message 1")]
    messages = LLMFunction._validate_messages(
        str_message="test message", messages=test_messages, role="system", allow_empty=False
    )

    assert len(messages) == 2
    assert messages[0].role == "system"
    assert messages[0].content[0].type == "text"
    assert messages[0].content[0].text == "test message"
    assert messages[1] == test_messages[0]


def test_validate_messages_none_not_allowed() -> None:
    with pytest.raises(ValueError, match="At least one of str message, messages is required"):
        LLMFunction._validate_messages(str_message=None, messages=None, role="system", allow_empty=False)


def test_validate_messages_none_allowed() -> None:
    messages = LLMFunction._validate_messages(str_message=None, messages=None, role="system", allow_empty=True)
    assert isinstance(messages, list)
    assert len(messages) == 0


def test_validate_messages_user_role() -> None:
    messages = LLMFunction._validate_messages(str_message="test message", messages=None, role="user", allow_empty=False)
    assert messages[0].role == "user"
