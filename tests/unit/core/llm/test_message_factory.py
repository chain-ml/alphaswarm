from alphaswarm.core.llm import Message


def test_message_basic():
    message = Message(role="system", content="test message")

    assert isinstance(message, Message)
    assert message.role == "system"
    assert message.content == "test message"


def test_system_message():
    message = Message.system("system test")

    assert isinstance(message, Message)
    assert message.role == "system"
    assert message.content == "system test"


def test_user_message():
    message = Message.user("user test")

    assert isinstance(message, Message)
    assert message.role == "user"
    assert message.content == "user test"


def test_assistant_message():
    message = Message.assistant("assistant test")

    assert isinstance(message, Message)
    assert message.role == "assistant"
    assert message.content == "assistant test"
