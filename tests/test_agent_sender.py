import pytest
import requests

from agent import sender
from agent.sender import get_health_url, send_data, validate_config


def test_get_health_url_uses_api_origin():
    assert get_health_url("https://inventario.example.com/checkin") == "https://inventario.example.com/"
    assert get_health_url("http://127.0.0.1:8000/api/checkin") == "http://127.0.0.1:8000/"


def test_validate_config_applies_defaults_and_rejects_invalid_values():
    config = validate_config({"api_url": "https://inventario.example.com/checkin", "agent_token": "token"})

    assert config["timeout"] == 10
    assert config["max_retries"] == 3
    assert config["retry_delay_seconds"] == 5

    config = validate_config({
        "api_url": "https://inventario.example.com/checkin",
        "agent_token": "token",
        "health_check_before_send": "false",
    })
    assert config["health_check_before_send"] is False

    config = validate_config({
        "api_url": "https://inventario.example.com/checkin",
        "agent_token": "token",
        "health_check_before_send": "true",
    })
    assert config["health_check_before_send"] is True

    with pytest.raises(ValueError, match="api_url"):
        validate_config({"api_url": "inventario.local/checkin", "agent_token": "token"})

    with pytest.raises(ValueError, match="max_retries"):
        validate_config({"api_url": "https://inventario.example.com/checkin", "agent_token": "token", "max_retries": 0})

    with pytest.raises(ValueError, match="retry_delay_seconds"):
        validate_config({"api_url": "https://inventario.example.com/checkin", "agent_token": "token", "retry_delay_seconds": -1})

    with pytest.raises(ValueError, match="health_check_before_send"):
        validate_config({
            "api_url": "https://inventario.example.com/checkin",
            "agent_token": "token",
            "health_check_before_send": "maybe",
        })


class FakeResponse:
    def __init__(self, payload=None, status_error=None, text="OK", status_code=200):
        self.payload = payload or {}
        self.status_error = status_error
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_error:
            raise self.status_error

    def json(self):
        return self.payload


def build_config(**overrides):
    config = {
        "api_url": "https://inventario.example.com/checkin",
        "agent_token": "agent-token",
        "timeout": 7,
        "max_retries": 3,
        "retry_delay_seconds": 2,
        "agent_version": "1.2.3",
    }
    config.update(overrides)
    return config


def test_send_data_posts_payload_with_agent_token(monkeypatch):
    monkeypatch.setattr(sender, "load_config", lambda: build_config())
    calls = []

    def fake_post(url, json, headers, timeout):
        calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return FakeResponse({"ok": True})

    monkeypatch.setattr(sender.requests, "post", fake_post)

    result = send_data({"hostname": "PC-01"})

    assert result == {"ok": True}
    assert calls == [
        {
            "url": "https://inventario.example.com/checkin",
            "json": {"hostname": "PC-01"},
            "headers": {"X-Agent-Token": "agent-token", "X-Agent-Version": "1.2.3"},
            "timeout": 7,
        }
    ]


def test_send_data_can_run_health_check_before_post(monkeypatch):
    monkeypatch.setattr(sender, "load_config", lambda: build_config(health_check_before_send=True))
    calls = []

    def fake_get(url, timeout):
        calls.append(("get", url, timeout))
        return FakeResponse({"health": "ok"})

    def fake_post(url, json, headers, timeout):
        calls.append(("post", url, timeout))
        return FakeResponse({"ok": True})

    monkeypatch.setattr(sender.requests, "get", fake_get)
    monkeypatch.setattr(sender.requests, "post", fake_post)

    result = send_data({"hostname": "PC-HEALTH"})

    assert result == {"ok": True}
    assert calls == [
        ("get", "https://inventario.example.com/", 7),
        ("post", "https://inventario.example.com/checkin", 7),
    ]


def test_send_data_retries_with_exponential_backoff(monkeypatch):
    monkeypatch.setattr(sender, "load_config", lambda: build_config())
    sleeps = []
    attempts = {"count": 0}

    def fake_post(url, json, headers, timeout):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise requests.Timeout("temporary timeout")
        return FakeResponse({"ok": True, "attempt": attempts["count"]})

    monkeypatch.setattr(sender.requests, "post", fake_post)
    monkeypatch.setattr(sender.time, "sleep", sleeps.append)

    result = send_data({"hostname": "PC-RETRY"})

    assert result == {"ok": True, "attempt": 3}
    assert sleeps == [2, 4]


def test_send_data_raises_last_request_error_after_retries(monkeypatch):
    monkeypatch.setattr(sender, "load_config", lambda: build_config(max_retries=2))
    sleeps = []

    def fake_post(url, json, headers, timeout):
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(sender.requests, "post", fake_post)
    monkeypatch.setattr(sender.time, "sleep", sleeps.append)

    with pytest.raises(requests.ConnectionError, match="offline"):
        send_data({"hostname": "PC-FAIL"})

    assert sleeps == [2]
