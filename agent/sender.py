import json
from pathlib import Path

import requests


BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def send_data(payload):
    config = load_config()
    api_url = config["api_url"]
    timeout = config.get("timeout", 10)

    response = requests.post(api_url, json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()