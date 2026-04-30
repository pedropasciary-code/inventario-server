import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

AGENT_TOKEN = os.getenv("AGENT_TOKEN")
SECRET_KEY = os.getenv("SECRET_KEY")
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
APP_TIMEZONE = os.getenv("APP_TIMEZONE", "America/Sao_Paulo")

# Comma-separated list of trusted reverse-proxy IPs allowed to set X-Forwarded-For.
# Use "*" to trust any proxy (only safe in fully controlled networks).
# Leave unset when the server is directly exposed (no proxy in front).
TRUSTED_PROXIES = os.getenv("TRUSTED_PROXIES", "")


def parse_non_negative_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as error:
        raise ValueError(f"{name} deve ser um numero inteiro: {raw_value}") from error
    if value < 0:
        raise ValueError(f"{name} nao pode ser negativo: {value}")
    return value


# How many days of asset check-in history to retain. Older records are purged
# automatically. Set to 0 to disable pruning.
CHECKIN_RETENTION_DAYS = parse_non_negative_int_env("CHECKIN_RETENTION_DAYS", 90)

if not AGENT_TOKEN:
    raise ValueError("AGENT_TOKEN não foi definido no arquivo .env")

if not SECRET_KEY:
    raise ValueError("SECRET_KEY não foi definido no arquivo .env")

try:
    DISPLAY_TIMEZONE = ZoneInfo(APP_TIMEZONE)
except Exception as error:
    raise ValueError(f"APP_TIMEZONE inválido: {APP_TIMEZONE}") from error
