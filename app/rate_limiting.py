from datetime import datetime, timedelta

from fastapi import HTTPException, Request

from .formatting import get_client_ip, utc_now


LOGIN_RATE_LIMIT_MAX_ATTEMPTS = 5
LOGIN_RATE_LIMIT_WINDOW = timedelta(minutes=15)
login_attempts: dict[str, list[datetime]] = {}

CHECKIN_RATE_LIMIT_MAX = 30
CHECKIN_RATE_LIMIT_WINDOW = timedelta(minutes=1)
checkin_attempts: dict[str, list[datetime]] = {}


def login_rate_limit_key(request: Request, username: str) -> str:
    return f"{get_client_ip(request)}:{username.lower().strip()}"


def prune_login_attempts(key: str, now: datetime):
    window_start = now - LOGIN_RATE_LIMIT_WINDOW
    attempts = [
        attempt
        for attempt in login_attempts.get(key, [])
        if attempt >= window_start
    ]
    if attempts:
        login_attempts[key] = attempts
    else:
        login_attempts.pop(key, None)
    return attempts


def enforce_login_rate_limit(request: Request, username: str):
    key = login_rate_limit_key(request, username)
    attempts = prune_login_attempts(key, utc_now())
    if len(attempts) >= LOGIN_RATE_LIMIT_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas de login. Tente novamente mais tarde.",
        )


def register_failed_login(request: Request, username: str):
    key = login_rate_limit_key(request, username)
    now = utc_now()
    attempts = prune_login_attempts(key, now)
    attempts.append(now)
    login_attempts[key] = attempts


def clear_failed_logins(request: Request, username: str):
    login_attempts.pop(login_rate_limit_key(request, username), None)


def prune_checkin_attempts(ip: str, now: datetime):
    window_start = now - CHECKIN_RATE_LIMIT_WINDOW
    attempts = [
        attempt
        for attempt in checkin_attempts.get(ip, [])
        if attempt >= window_start
    ]
    if attempts:
        checkin_attempts[ip] = attempts
    else:
        checkin_attempts.pop(ip, None)
    return attempts


def enforce_checkin_rate_limit(request: Request):
    ip = get_client_ip(request)
    now = utc_now()
    attempts = prune_checkin_attempts(ip, now)
    if len(attempts) >= CHECKIN_RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=429,
            detail="Limite de check-ins excedido. Tente novamente em alguns minutos.",
        )
    attempts.append(now)
    checkin_attempts[ip] = attempts
