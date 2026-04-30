import json
from datetime import UTC, datetime

from fastapi import Request

from .config import DISPLAY_TIMEZONE
from .utils import utc_now


def ensure_utc(value: datetime | None) -> datetime | None:
    if not value:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def format_datetime(value: datetime | None) -> str:
    value = ensure_utc(value)
    if not value:
        return ""
    return value.astimezone(DISPLAY_TIMEZONE).strftime("%d/%m/%Y %H:%M")


def format_json(value: str | None) -> str:
    if not value:
        return "{}"
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return value
    return json.dumps(parsed, ensure_ascii=False, indent=2, sort_keys=True)


def parse_network_interfaces(value: str | None) -> list[dict]:
    if not value:
        return []
    try:
        interfaces = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(interfaces, list):
        return []
    return [interface for interface in interfaces if isinstance(interface, dict)]


def get_client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None
