import json
import time
from pathlib import Path

import requests


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


def send_data(payload):
    config = load_config()
    api_url = config["api_url"]
    timeout = config.get("timeout", 10)
    agent_token = config["agent_token"]
    max_retries = config.get("max_retries", 3)
    retry_delay_seconds = config.get("retry_delay_seconds", 5)

    headers = {
        "X-Agent-Token": agent_token
    }

    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                api_url,
                json=payload,
                headers=headers,
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()

        except requests.RequestException as error:
            last_error = error

            if attempt < max_retries:
                time.sleep(retry_delay_seconds)

    raise last_error