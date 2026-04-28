import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

sys.path.append(str(BASE_DIR))

from collector import get_system_info
from sender import send_data, load_config


LOG_FILE = BASE_DIR / "agent.log"
FAILED_PAYLOADS_DIR = BASE_DIR / "failed_payloads"
FAILED_PAYLOADS_DIR.mkdir(exist_ok=True)


logger = logging.getLogger()
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=1_000_000,
    backupCount=5,
    encoding="utf-8"
)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

logger.handlers.clear()
logger.addHandler(file_handler)
logger.addHandler(console_handler)


def save_failed_payload(payload):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = FAILED_PAYLOADS_DIR / f"payload_{timestamp}.json"

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    logging.warning(f"Payload salvo para reenvio posterior: {file_path}")


def resend_failed_payloads():
    failed_files = sorted(FAILED_PAYLOADS_DIR.glob("payload_*.json"))

    if not failed_files:
        logging.info("Nenhum payload pendente para reenvio")
        return

    logging.info(f"Encontrados {len(failed_files)} payload(s) pendente(s) para reenvio")

    for file_path in failed_files:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                payload = json.load(file)

            send_data(payload)
            file_path.unlink()

            logging.info(f"Payload reenviado com sucesso e removido: {file_path.name}")

        except Exception as error:
            logging.error(f"Falha ao reenviar {file_path.name}: {error}")


def main():
    try:
        config = load_config()
        agent_version = config.get("agent_version", "unknown")

        logging.info(f"Iniciando agent versão {agent_version}")

        resend_failed_payloads()

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