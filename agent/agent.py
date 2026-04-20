from pathlib import Path
from datetime import datetime
import sys

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

from collector import get_system_info
from sender import send_data

LOG_FILE = BASE_DIR / "agent.log"


def write_log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as file:
        file.write(f"[{timestamp}] {message}\n")


def main():
    try:
        data = get_system_info()
        write_log(f"Dados coletados: {data}")

        response = send_data(data)
        write_log(f"Envio realizado com sucesso: {response}")

        print("Dados enviados com sucesso.")
        print(response)

    except Exception as error:
        write_log(f"Erro ao executar agent: {error}")
        print("Erro ao executar agent:")
        print(error)


if __name__ == "__main__":
    main()