import pytest
import requests

from agent import sender
from agent.sender import get_health_url, send_data


def test_get_health_url_uses_api_origin():
    assert get_health_url("https://inventario.example.com/checkin") == "https://inventario.example.com/"
    assert get_health_url("http://127.0.0.1:8000/api/checkin") == "http://127.0.0.1:8000/"


class FakeResponse:
    def __init__(self, payload=None, status_error=None):
        self.payload = payload or {}
        self.status_error = status_error

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
            "headers": {"X-Agent-Token": "agent-token"},
            "timeout": 7,
        }
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
