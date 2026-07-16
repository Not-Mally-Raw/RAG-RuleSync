import pytest

from dfm_rule_pipeline.llm.client import LLMClient


class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeChoice:
    def __init__(self, content):
        self.message = FakeMessage(content)


class FakeResponse:
    def __init__(self, content):
        self.choices = [FakeChoice(content)]


class FakeCompletions:
    def __init__(self, owner):
        self.owner = owner

    def create(self, **kwargs):
        self.owner.calls.append(kwargs)
        if self.owner.error:
            raise self.owner.error
        return FakeResponse(self.owner.content)


class FakeChat:
    def __init__(self, owner):
        self.completions = FakeCompletions(owner)


class FakeGroqClient:
    def __init__(self, content=None, error=None):
        self.content = content
        self.error = error
        self.calls = []
        self.chat = FakeChat(self)


def make_client(fake_clients):
    client = LLMClient.__new__(LLMClient)
    client.clients = fake_clients
    client.model = "test-model"
    client.max_tokens = 4096
    client.current_client_idx = 0
    return client


def test_llm_client_falls_back_to_next_key_after_failure():
    failed = FakeGroqClient(error=Exception("invalid_api_key"))
    working = FakeGroqClient(content="ok")
    client = make_client([failed, working])

    assert client.call("hello") == "ok"
    assert len(failed.calls) == 1
    assert len(working.calls) == 1
    assert working.calls[0]["max_tokens"] == 4096
    assert client.current_client_idx == 0


def test_llm_client_can_request_json_mode():
    working = FakeGroqClient(content='{"ok": true}')
    client = make_client([working])

    assert client.call("hello", json_mode=True) == '{"ok": true}'
    assert working.calls[0]["response_format"] == {"type": "json_object"}


def test_llm_client_reports_all_failed_keys():
    client = make_client([
        FakeGroqClient(error=Exception("invalid_api_key")),
        FakeGroqClient(error=Exception("rate_limit_exceeded")),
    ])

    with pytest.raises(Exception) as exc_info:
        client.call("hello")

    message = str(exc_info.value)
    assert "All Groq API keys failed after 2 attempts" in message
    assert "Key #1" in message
    assert "Key #2" in message
