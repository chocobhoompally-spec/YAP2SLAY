import sys
from types import SimpleNamespace

from backend import assistant


class FakeApiError(Exception):
    def __init__(self, message, code=None, status_code=None):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def test_error_log_includes_status_and_redacts_credentials(monkeypatch, capsys):
    api_key = "opaque-environment-secret-value"
    google_key = "AIzaSyA-very-private-test-key-123456"
    bearer = "private-bearer-token-value"
    monkeypatch.setenv("GEMINI_API_KEY", api_key)
    error = FakeApiError(
        f"INVALID_ARGUMENT api_key={api_key}; echoed={api_key}; Authorization: Bearer {bearer}; "
        f'x-goog-api-key: "{google_key}"',
        code=400,
    )

    assistant._log("send", error)

    output = capsys.readouterr().out
    assert "HTTP 400" in output
    assert "INVALID_ARGUMENT" in output
    assert api_key not in output
    assert google_key not in output
    assert bearer not in output
    assert "[REDACTED" in output


def test_initialization_failure_is_logged_without_key(monkeypatch, capsys):
    from google import genai

    api_key = "initialization-private-key-value"
    monkeypatch.setattr(
        assistant,
        "_setting",
        lambda name, default="": api_key if name == "GEMINI_API_KEY" else default,
    )

    def fail_client(**kwargs):
        raise FakeApiError(f"bad key api_key={api_key}", status_code=401)

    monkeypatch.setattr(genai, "Client", fail_client)

    chat = assistant.new_chat()
    output = capsys.readouterr().out
    assert isinstance(chat, assistant._UnavailableChat)
    assert "[assistant:init]" in output
    assert "HTTP 401" in output
    assert "HTTP 401" in chat.diagnostic
    assert "configured credentials" in chat.diagnostic
    assert api_key not in output
    assert "bad key" in output
    monkeypatch.setattr(assistant, "new_chat", lambda: chat)
    monkeypatch.setattr(assistant.db, "latest_action_id", lambda: 0)
    monkeypatch.setattr(assistant.db, "actions_since", lambda action_id: [])
    reply = assistant.send(chat, "hello")["reply"]
    assert "HTTP 401" in reply
    assert "configured credentials" in reply
    assert api_key not in reply


def test_client_uses_gemini_api_even_when_vertex_environment_flags_are_set(monkeypatch):
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_GENAI_USE_ENTERPRISE", "true")
    monkeypatch.setattr(
        assistant,
        "_setting",
        lambda name, default="": "test-gemini-api-key" if name == "GEMINI_API_KEY" else default,
    )

    client = assistant._make_client()

    assert client is not None
    assert client._api_client.vertexai is False
    assert client._api_client._http_options.base_url == "https://generativelanguage.googleapis.com/"


def test_streamlit_gemini_secret_wins_over_stale_environment_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "stale-environment-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "unrelated-google-key")
    monkeypatch.setitem(
        sys.modules,
        "streamlit",
        SimpleNamespace(secrets={"GEMINI_API_KEY": "intended-streamlit-key"}),
    )

    assert assistant._setting("GEMINI_API_KEY") == "intended-streamlit-key"


def test_google_api_key_is_only_a_fallback(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "legacy-google-key")
    monkeypatch.setitem(
        sys.modules,
        "streamlit",
        SimpleNamespace(secrets={}),
    )

    assert assistant._setting("GEMINI_API_KEY") == "legacy-google-key"


def test_streamlit_google_secret_fallback_wins_over_stale_environment(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "stale-environment-key")
    monkeypatch.setitem(
        sys.modules,
        "streamlit",
        SimpleNamespace(secrets={"GOOGLE_API_KEY": "configured-google-secret"}),
    )

    assert assistant._setting("GEMINI_API_KEY") == "configured-google-secret"


def test_chat_creation_failure_is_logged(monkeypatch, capsys):
    api_key = "chat-creation-private-key"
    monkeypatch.setattr(assistant, "_setting", lambda name, default="": api_key)

    class Chats:
        def create(self, **kwargs):
            raise FakeApiError("model unavailable; check model configuration", code=404)

    class Client:
        chats = Chats()

    monkeypatch.setattr(assistant, "_make_client", lambda: Client())

    result = assistant.new_chat()
    output = capsys.readouterr().out
    assert isinstance(result, assistant._UnavailableChat)
    assert "[assistant:new_chat]" in output
    assert "HTTP 404" in output
    assert "model unavailable" in output
    assert api_key not in output
    assert "HTTP 404" in result.diagnostic
    assert "could not find" in result.diagnostic


def test_message_send_failure_logs_details_but_returns_friendly_reply(monkeypatch, capsys):
    api_key = "message-send-private-key"
    monkeypatch.setattr(
        assistant,
        "_setting",
        lambda name, default="": api_key if name == "GEMINI_API_KEY" else default,
    )
    monkeypatch.setattr(assistant.db, "latest_action_id", lambda: 0)
    monkeypatch.setattr(assistant.db, "actions_since", lambda action_id: [])

    class BrokenChat:
        def send_message(self, message):
            raise FakeApiError(
                f"request rejected: INVALID_ARGUMENT api_key={api_key}; Authorization: Bearer {api_key}",
                status_code=400,
            )

    result = assistant.send(BrokenChat(), "hello")
    output = capsys.readouterr().out
    assert "[assistant:send]" in output
    assert "HTTP 400" in output
    assert "INVALID_ARGUMENT" in output
    assert "HTTP 400" in result["reply"]
    assert "check request configuration" in result["reply"]
    assert "INVALID_ARGUMENT" not in result["reply"]
    assert api_key not in result["reply"]
    assert api_key not in output


def test_new_chat_uses_flash_lite_with_existing_function_tools(monkeypatch):
    captured = {}

    class Chats:
        def create(self, **kwargs):
            captured.update(kwargs)
            return object()

    class Client:
        chats = Chats()

    monkeypatch.setattr(
        assistant,
        "_setting",
        lambda name, default="": "test-key" if name == "GEMINI_API_KEY" else default,
    )
    monkeypatch.setattr(assistant, "_make_client", lambda: Client())

    chat = assistant.new_chat()

    assert isinstance(chat, assistant._ManagedChat)
    assert captured["model"] == "gemini-3.5-flash-lite"
    assert captured["config"].tools == assistant.tools.ALL_TOOLS


def test_rate_limit_reply_does_not_guess_a_retry_delay(monkeypatch):
    api_key = "test-key"
    monkeypatch.setattr(
        assistant,
        "_setting",
        lambda name, default="": api_key if name == "GEMINI_API_KEY" else default,
    )
    monkeypatch.setattr(assistant.db, "latest_action_id", lambda: 0)
    monkeypatch.setattr(assistant.db, "actions_since", lambda action_id: [])

    class RateLimitedChat:
        calls = 0

        def send_message(self, message):
            self.calls += 1
            raise FakeApiError("quota exhausted", status_code=429)

    chat = RateLimitedChat()
    result = assistant.send(chat, "help me plan")

    assert chat.calls == 1
    assert "quota or rate limit was reached" in result["reply"]
    assert "Google AI Studio" in result["reply"]
    assert "60 seconds" not in result["reply"]
