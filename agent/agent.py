from pathlib import Path
from datetime import datetime
import sys

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

from collector import get_system_info
from sender import send_data

LOG_FILE = BASE_DIR / "agent.log"


def write_log(message):
    # Registra eventos do agent com timestamp para facilitar auditoria e suporte.
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as file:
        file.write(f"[{timestamp}] {message}\n")


def main():
    try:
        # Coleta os dados locais da máquina antes de qualquer comunicação externa.
        data = get_system_info()
        write_log(f"Dados coletados: {data}")

        # Envia o inventário para a API central e registra a resposta recebida.
        response = send_data(data)
        write_log(f"Envio realizado com sucesso: {response}")

        print("Dados enviados com sucesso.")
        print(response)

    except Exception as error:
        # Qualquer falha é registrada em log e também exibida na execução manual.
        write_log(f"Erro ao executar agent: {error}")
        print("Erro ao executar agent:")
        print(error)


if __name__ == "__main__":
    # Permite executar o agent diretamente pela linha de comando.
    main()
