import json
import logging
import sys
import argparse
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Define a pasta base tanto quando o agent roda como script Python quanto quando
# roda empacotado pelo PyInstaller como executável.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

# Inclui a pasta do agent no path para permitir importar módulos locais no exe.
sys.path.append(str(BASE_DIR))

from collector import get_system_info
from sender import send_data, load_config, check_api_health


# Arquivos de apoio usados para registrar execução e guardar coletas que falharam.
LOG_FILE = BASE_DIR / "agent.log"
FAILED_PAYLOADS_DIR = BASE_DIR / "failed_payloads"
FAILED_PAYLOADS_DIR.mkdir(exist_ok=True)


# Configura logging com rotação para evitar que o log cresça indefinidamente.
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
    # Salva o payload em JSON para que uma próxima execução tente reenviar.
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = FAILED_PAYLOADS_DIR / f"payload_{timestamp}.json"

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    logging.warning(f"Payload salvo para reenvio posterior: {file_path}")


def resend_failed_payloads():
    # Procura coletas antigas que não chegaram ao servidor em execuções anteriores.
    failed_files = sorted(FAILED_PAYLOADS_DIR.glob("payload_*.json"))

    if not failed_files:
        logging.info("Nenhum payload pendente para reenvio")
        return

    logging.info(f"Encontrados {len(failed_files)} payload(s) pendente(s) para reenvio")

    for file_path in failed_files:
        try:
            # Recarrega cada payload pendente e remove o arquivo apenas após envio OK.
            with open(file_path, "r", encoding="utf-8") as file:
                payload = json.load(file)

            send_data(payload)
            file_path.unlink()

            logging.info(f"Payload reenviado com sucesso e removido: {file_path.name}")

        except Exception as error:
            logging.error(f"Falha ao reenviar {file_path.name}: {error}")


def diagnose():
    print("Diagnóstico do RDP System Agent")

    config = load_config()
    print(f"Config carregada: {BASE_DIR / 'config.json'}")
    print(f"API URL: {config.get('api_url')}")
    print(f"Token configurado: {'sim' if config.get('agent_token') else 'não'}")
    print(f"Versão do agent: {config.get('agent_version', 'unknown')}")

    data = get_system_info()
    print(f"Hostname: {data.get('hostname')}")
    print(f"Serial: {data.get('serial') or 'não coletado'}")
    print(f"IP principal: {data.get('ip') or 'não coletado'}")
    print(f"MAC principal: {data.get('mac_address') or 'não coletado'}")
    print(f"Interfaces de rede: {len(data.get('network_interfaces') or [])}")

    health = check_api_health()
    print(f"API acessível: {health['url']} ({health['status_code']})")


def main():
    parser = argparse.ArgumentParser(description="Executa o RDP System Agent.")
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="Valida configuração, coleta local e conectividade sem enviar check-in.",
    )
    args = parser.parse_args()

    if args.diagnose:
        try:
            diagnose()
            return
        except Exception as error:
            logging.error(f"Erro no diagnóstico do agent: {error}")
            print("Erro no diagnóstico do agent:")
            print(error)
            return

    # Fluxo principal: carrega configuração, reenvia pendências, coleta e envia dados.
    try:
        config = load_config()
        agent_version = config.get("agent_version", "unknown")

        logging.info(f"Iniciando agent versão {agent_version}")

        resend_failed_payloads()

        # Coleta as informações locais do Windows e adiciona a versão do agent ao envio.
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
            # Se a coleta foi concluída mas o envio falhou, guarda o payload para retry.
            if "data" in locals():
                save_failed_payload(data)
        except Exception as payload_error:
            logging.error(f"Erro ao salvar payload com falha: {payload_error}")

        print("Erro ao executar agent:")
        print(error)


if __name__ == "__main__":
    # Permite executar o arquivo diretamente pelo Python ou pelo executável empacotado.
    main()
