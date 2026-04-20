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
    agent_token = config["agent_token"]

    headers = {
        "X-Agent-Token": agent_token
    }

    response = requests.post(api_url, json=payload, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.json()