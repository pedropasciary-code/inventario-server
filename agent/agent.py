import json
import logging
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

from collector import get_system_info
from sender import send_data, load_config


LOG_FILE = BASE_DIR / "agent.log"
FAILED_PAYLOADS_DIR = BASE_DIR / "failed_payloads"
FAILED_PAYLOADS_DIR.mkdir(exist_ok=True)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)


def save_failed_payload(payload):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = FAILED_PAYLOADS_DIR / f"payload_{timestamp}.json"

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    logging.warning(f"Payload salvo para reenvio manual: {file_path}")


def main():
    try:
        config = load_config()
        agent_version = config.get("agent_version", "unknown")

        logging.info(f"Iniciando agent versão {agent_version}")

        data = get_system_info()
        data["agent_version"] = agent_version

        logging.info("Dados coletados com sucesso")
        logging.info(f"Hostname: {data.get('hostname')} | Serial: {data.get('serial')}")

        response = send_data(data)

        logging.info("Envio realizado com sucesso")
        logging.info(f"Resposta da API: {response}")

        print("Dados enviados com sucesso.")
        print(response)

    except Exception as error:
        logging.error(f"Erro ao executar agent: {error}")

        try:
            if "data" in locals():
                save_failed_payload(data)
        except Exception as payload_error:
            logging.error(f"Erro ao salvar payload com falha: {payload_error}")

        print("Erro ao executar agent:")
        print(error)


if __name__ == "__main__":
    main()