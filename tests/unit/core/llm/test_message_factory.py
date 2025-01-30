from alphaswarm.core.llm import MessageFactory


def test_message_basic():
    message = MessageFactory.message(role="system", content="test message")
    assert isinstance(message, dict)
    assert message["role"] == "system"
    assert message["content"] == "test message"


def test_message_with_cache():
    message = MessageFactory.message(role="user", content="cached message", cache=True)
    assert isinstance(message, dict)
    assert message["role"] == "user"
    assert isinstance(message["content"], list)
    assert len(message["content"]) == 1
    assert message["content"][0]["type"] == "text"
    assert message["content"][0]["text"] == "cached message"
    assert message["content"][0]["cache_control"]["type"] == "ephemeral"


def test_system_message():
    message = MessageFactory.system_message("system test")
    assert message["role"] == "system"
    assert message["content"] == "system test"


def test_system_message_with_cache():
    message = MessageFactory.system_message("system test with cache", cache=True)
    assert message["role"] == "system"
    assert isinstance(message["content"], list)
    assert message["content"][0]["text"] == "system test with cache"


def test_user_message():
    message = MessageFactory.user_message("user test")
    assert message["role"] == "user"
    assert message["content"] == "user test"


def test_user_message_with_cache():
    message = MessageFactory.user_message("user test with cache", cache=True)
    assert message["role"] == "user"
    assert isinstance(message["content"], list)
    assert message["content"][0]["text"] == "user test with cache"


def test_assistant_message():
    message = MessageFactory.assistant_message("assistant test")
    assert message["role"] == "assistant"
    assert message["content"] == "assistant test"


def test_assistant_message_with_cache():
    message = MessageFactory.assistant_message("assistant test with cache", cache=True)
    assert message["role"] == "assistant"
    assert isinstance(message["content"], list)
    assert message["content"][0]["text"] == "assistant test with cache"
