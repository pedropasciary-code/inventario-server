import argparse
import getpass
import os

from app.auth import hash_password
from app.database import SessionLocal
from app.models import User


def get_credentials():
    # Permite automação por argumento/env e fallback interativo sem senha hardcoded.
    parser = argparse.ArgumentParser(description="Cria um usuário do painel de inventário.")
    parser.add_argument("--username", default=os.getenv("INVENTARIO_ADMIN_USER"))
    parser.add_argument("--password", default=os.getenv("INVENTARIO_ADMIN_PASSWORD"))
    args = parser.parse_args()

    username = args.username or input("Usuário: ").strip()
    password = args.password

    if not username:
        raise ValueError("Usuário não pode ficar vazio.")

    if not password:
        password = getpass.getpass("Senha: ")
        password_confirmation = getpass.getpass("Confirme a senha: ")

        if password != password_confirmation:
            raise ValueError("As senhas informadas não conferem.")

    if len(password) < 8:
        raise ValueError("A senha deve ter pelo menos 8 caracteres.")

    return username, password


def create_user(username: str, password: str):
    # Abre uma sessão direta no banco para executar o cadastro inicial manualmente.
    db = SessionLocal()

    try:
        # Verifica se o usuário já existe para evitar duplicidade.
        existing_user = db.query(User).filter(User.username == username).first()

        if existing_user:
            print("Usuário já existe.")
            return

        # Persiste o novo usuário já com a senha protegida por hash.
        user = User(
            username=username,
            password_hash=hash_password(password),
            is_active=True
        )
        db.add(user)
        db.commit()

        print("Usuário criado com sucesso.")
        print(f"Usuário: {username}")
    finally:
        # Fecha a conexão aberta manualmente ao final do script.
        db.close()


if __name__ == "__main__":
    username, password = get_credentials()
    create_user(username, password)
