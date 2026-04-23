import json
from pathlib import Path

import requests


BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"


def load_config():
    # Lê a configuração local do agent com URL da API, token e timeout.
    with open(CONFIG_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def send_data(payload):
    # Carrega os parâmetros de conexão antes de montar a requisição.
    config = load_config()
    api_url = config["api_url"]
    timeout = config.get("timeout", 10)
    agent_token = config["agent_token"]

    # Envia o token em header para que a API valide a origem do check-in.
    headers = {
        "X-Agent-Token": agent_token
    }

    # Faz o POST do inventário para o backend central usando JSON.
    response = requests.post(api_url, json=payload, headers=headers, timeout=timeout)

    # Interrompe o fluxo se a API responder com erro HTTP.
    response.raise_for_status()

    # Retorna o corpo da resposta já convertido para dicionário.
    return response.json()
