"""Tests for the redaction pipeline."""

from __future__ import annotations

from agentscope.core.models import EventType, TraceEvent
from agentscope.core.redaction import RedactionPipeline


def test_redact_openai_key():
    r = RedactionPipeline()
    text = "My key is sk-abc123def456ghi789jkl012mno345pqr"
    result = r.redact_text(text)
    assert "sk-***" in result
    assert "sk-abc" not in result


def test_redact_github_token():
    r = RedactionPipeline()
    text = "Token: ghp_ABC...1234"
    result = r.redact_text(text)
    # The generic token= pattern catches it first, or the ghp_ pattern does
    assert "***" in result
    assert "ghp_ABC" not in result


def test_redact_api_key_in_dict():
    r = RedactionPipeline()
    data = {"api_key": "secret123", "name": "test"}
    result = r.redact_dict(data)
    assert result["api_key"] == "***"
    assert result["name"] == "test"


def test_redact_password_in_dict():
    r = RedactionPipeline()
    data = {"password": "hunter2", "username": "admin"}
    result = r.redact_dict(data)
    assert result["password"] == "***"
    assert result["username"] == "admin"


def test_redact_bearer_token():
    r = RedactionPipeline()
    text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz"
    result = r.redact_text(text)
    assert "Bearer ***" in result


def test_redact_connection_string():
    r = RedactionPipeline()
    text = "postgresql://user:supersecret@localhost:5432/mydb"
    result = r.redact_text(text)
    assert "supersecret" not in result
    assert "***" in result


def test_redact_private_key():
    r = RedactionPipeline()
    text = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----"
    result = r.redact_text(text)
    assert "MIIEpAIBAAKCAQEA" not in result
    assert "***" in result


def test_redact_nested_dict():
    r = RedactionPipeline()
    data = {
        "config": {
            "api_key": "secret",
            "nested": {"token": "another-secret"},
        },
        "safe": "visible",
    }
    result = r.redact_dict(data)
    assert result["config"]["api_key"] == "***"
    assert result["config"]["nested"]["token"] == "***"
    assert result["safe"] == "visible"


def test_redact_list():
    r = RedactionPipeline()
    data = ["normal", "sk-secretkey12345678901234567890", {"api_key": "x"}]
    result = r.redact_list(data)
    assert result[0] == "normal"
    assert "sk-***" in result[1]
    assert result[2]["api_key"] == "***"


def test_redact_event():
    r = RedactionPipeline()
    event = TraceEvent(
        run_id="test",
        event_type=EventType.TOOL_CALL,
        data={"api_key": "secret123", "cmd": "ls"},
    )
    result = r.redact_event(event)
    assert result.data["api_key"] == "***"
    assert result.data["cmd"] == "ls"


def test_redact_preserves_safe_text():
    r = RedactionPipeline()
    text = "This is a normal log message with no secrets"
    result = r.redact_text(text)
    assert result == text


def test_extra_patterns():
    r = RedactionPipeline(extra_patterns=[(r"MY_CUSTOM_\w+", "CUSTOM_REDACTED")])
    text = "Value: MY_CUSTOM_SECRET"
    result = r.redact_text(text)
    assert "CUSTOM_REDACTED" in result
    assert "MY_CUSTOM_SECRET" not in result
