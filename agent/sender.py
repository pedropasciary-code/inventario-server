import json
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


def load_config():
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Arquivo de configuração não encontrado: {CONFIG_FILE}")

    with open(CONFIG_FILE, "r", encoding="utf-8") as file:
        config = json.load(file)

    required_keys = ["api_url", "agent_token"]
    for key in required_keys:
        if key not in config or not config[key]:
            raise ValueError(f"Configuração obrigatória ausente: {key}")

    return config


def get_health_url(api_url):
    parsed_url = urlparse(api_url)
    return urlunparse((parsed_url.scheme, parsed_url.netloc, "/", "", "", ""))


def check_api_health():
    config = load_config()
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

    headers = {"X-Agent-Token": agent_token}
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(api_url, json=payload, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.json()

        except requests.RequestException as error:
            last_error = error

            if attempt < max_retries:
                # Exponential backoff: 5s, 10s, 20s, ... capped at 5 minutes
                delay = min(retry_delay_seconds * (2 ** (attempt - 1)), 300)
                time.sleep(delay)

    raise last_error
