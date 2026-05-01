import threading
from datetime import datetime, timedelta

from fastapi import HTTPException, Request

from .config import CHECKIN_RATE_LIMIT_MAX, LOGIN_RATE_LIMIT_MAX_ATTEMPTS
from .formatting import get_client_ip
from .utils import utc_now


LOGIN_RATE_LIMIT_WINDOW = timedelta(minutes=15)
login_attempts: dict[str, list[datetime]] = {}

CHECKIN_RATE_LIMIT_WINDOW = timedelta(minutes=1)
checkin_attempts: dict[str, list[datetime]] = {}

# NOTE: these dicts are in-process. With multiple uvicorn workers (--workers N)
# each process has its own counters, making the effective limit N times higher.
# For multi-worker deployments, replace with a shared store such as Redis.
_lock = threading.Lock()


def login_rate_limit_key(request: Request, username: str) -> str:
    ip = get_client_ip(request) or "unknown"
    return f"{ip}:{username.lower().strip()}"


def _prune(attempts_dict: dict, key: str, window: timedelta, now: datetime) -> list[datetime]:
    window_start = now - window
    fresh = [t for t in attempts_dict.get(key, []) if t >= window_start]
    if fresh:
        attempts_dict[key] = fresh
    else:
        attempts_dict.pop(key, None)
    return fresh


def cleanup_stale_entries():
    now = utc_now()
    with _lock:
        login_cutoff = now - LOGIN_RATE_LIMIT_WINDOW
        stale_login = [k for k, times in login_attempts.items() if not any(t >= login_cutoff for t in times)]
        for k in stale_login:
            del login_attempts[k]

        checkin_cutoff = now - CHECKIN_RATE_LIMIT_WINDOW
        stale_checkin = [k for k, times in checkin_attempts.items() if not any(t >= checkin_cutoff for t in times)]
        for k in stale_checkin:
            del checkin_attempts[k]


def enforce_login_rate_limit(request: Request, username: str):
    key = login_rate_limit_key(request, username)
    with _lock:
        attempts = _prune(login_attempts, key, LOGIN_RATE_LIMIT_WINDOW, utc_now())
    if len(attempts) >= LOGIN_RATE_LIMIT_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas de login. Tente novamente mais tarde.",
        )


def register_failed_login(request: Request, username: str):
    key = login_rate_limit_key(request, username)
    now = utc_now()
    with _lock:
        attempts = _prune(login_attempts, key, LOGIN_RATE_LIMIT_WINDOW, now)
        attempts.append(now)
        login_attempts[key] = attempts


def clear_failed_logins(request: Request, username: str):
    key = login_rate_limit_key(request, username)
    with _lock:
        login_attempts.pop(key, None)


def checkin_rate_limit_key(request: Request, asset_data: dict | None = None) -> str:
    ip = get_client_ip(request) or "unknown"
    asset_data = asset_data or {}
    identity = (
        asset_data.get("serial")
        or asset_data.get("mac_address")
        or asset_data.get("hostname")
        or "unknown"
    )
    return f"{ip}:{str(identity).lower().strip()}"


def enforce_checkin_rate_limit(request: Request, asset_data: dict | None = None):
    key = checkin_rate_limit_key(request, asset_data)
    now = utc_now()
    with _lock:
        attempts = _prune(checkin_attempts, key, CHECKIN_RATE_LIMIT_WINDOW, now)
        if len(attempts) >= CHECKIN_RATE_LIMIT_MAX:
            raise HTTPException(
                status_code=429,
                detail="Limite de check-ins excedido. Tente novamente em alguns minutos.",
            )
        attempts.append(now)
        checkin_attempts[key] = attempts
