import json
import logging
import time
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import requests

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

CONFIG_FILE = BASE_DIR / "config.json"
logger = logging.getLogger(__name__)


def _positive_number(value, field_name):
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Configuracao invalida para {field_name}: {value}") from error
    if number <= 0:
        raise ValueError(f"Configuracao invalida para {field_name}: deve ser maior que zero")
    return number


def _non_negative_number(value, field_name):
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Configuracao invalida para {field_name}: {value}") from error
    if number < 0:
        raise ValueError(f"Configuracao invalida para {field_name}: nao pode ser negativo")
    return number


def _optional_bool(value, field_name):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "sim"}:
            return True
        if normalized in {"false", "0", "no", "nao", "não"}:
            return False
    raise ValueError(f"Configuracao invalida para {field_name}: use true ou false")


def validate_config(config):
    required_keys = ["api_url", "agent_token"]
    for key in required_keys:
        if key not in config or not config[key]:
            raise ValueError(f"Configuracao obrigatoria ausente: {key}")

    parsed_url = urlparse(config["api_url"])
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError("Configuracao invalida para api_url: use uma URL http(s) completa")

    config["timeout"] = _positive_number(config.get("timeout", 10), "timeout")

    try:
        max_retries = int(config.get("max_retries", 3))
    except (TypeError, ValueError) as error:
        raise ValueError(f"Configuracao invalida para max_retries: {config.get('max_retries')}") from error
    if max_retries < 1:
        raise ValueError("Configuracao invalida para max_retries: deve ser pelo menos 1")
    config["max_retries"] = max_retries
    config["retry_delay_seconds"] = _non_negative_number(
        config.get("retry_delay_seconds", 5),
        "retry_delay_seconds",
    )

    if "health_check_before_send" in config:
        config["health_check_before_send"] = _optional_bool(
            config["health_check_before_send"],
            "health_check_before_send",
        )

    return config


def load_config():
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Arquivo de configuração não encontrado: {CONFIG_FILE}")

    with open(CONFIG_FILE, "r", encoding="utf-8") as file:
        config = json.load(file)

    return validate_config(config)


def get_health_url(api_url):
    parsed_url = urlparse(api_url)
    return urlunparse((parsed_url.scheme, parsed_url.netloc, "/", "", "", ""))


def check_api_health(config=None):
    config = config or load_config()
    timeout = config.get("timeout", 10)
    health_url = config.get("health_url") or get_health_url(config["api_url"])

    response = requests.get(health_url, timeout=timeout)
    response.raise_for_status()
    return {
        "url": health_url,
        "status_code": response.status_code,
        "body": response.text[:200],
    }


def send_data(payload):
    config = load_config()
    api_url = config["api_url"]
    timeout = config.get("timeout", 10)
    agent_token = config["agent_token"]
    max_retries = config.get("max_retries", 3)
    retry_delay_seconds = config.get("retry_delay_seconds", 5)
    agent_version = config.get("agent_version")

    headers = {"X-Agent-Token": agent_token}
    if agent_version:
        headers["X-Agent-Version"] = str(agent_version)
    last_error = None

    if config.get("health_check_before_send", False):
        health = check_api_health(config)
        logger.info("Health-check da API OK: %s (%s)", health["url"], health["status_code"])

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Enviando payload para API (tentativa %s/%s)", attempt, max_retries)
            response = requests.post(api_url, json=payload, headers=headers, timeout=timeout)
            response.raise_for_status()
            logger.info("Payload enviado com sucesso")
            return response.json()

        except requests.RequestException as error:
            last_error = error
            logger.warning("Falha ao enviar payload na tentativa %s/%s: %s", attempt, max_retries, error)

            if attempt < max_retries:
                # Exponential backoff: 5s, 10s, 20s, ... capped at 5 minutes
                delay = min(retry_delay_seconds * (2 ** (attempt - 1)), 300)
                logger.info("Aguardando %.1f segundo(s) antes da próxima tentativa", delay)
                time.sleep(delay)

    raise last_error
