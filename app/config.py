import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

# Carrega as credenciais e chaves de configuração usadas pela aplicação.
load_dotenv()

AGENT_TOKEN = os.getenv("AGENT_TOKEN")
SECRET_KEY = os.getenv("SECRET_KEY")
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
APP_TIMEZONE = os.getenv("APP_TIMEZONE", "America/Sao_Paulo")

if not AGENT_TOKEN:
    raise ValueError("AGENT_TOKEN não foi definido no arquivo .env")

if not SECRET_KEY:
    raise ValueError("SECRET_KEY não foi definido no arquivo .env")

try:
    DISPLAY_TIMEZONE = ZoneInfo(APP_TIMEZONE)
except Exception as error:
    raise ValueError(f"APP_TIMEZONE inválido: {APP_TIMEZONE}") from error
