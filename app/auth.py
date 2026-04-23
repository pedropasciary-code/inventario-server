import hashlib
import hmac
import os
import secrets


def hash_password(password: str) -> str:
    # Gera um salt aleatório por senha para evitar hashes repetidos entre usuários.
    salt = secrets.token_hex(16)
    iterations = 100_000

    # Usa PBKDF2-HMAC-SHA256 para derivar um hash forte a partir da senha informada.
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations
    ).hex()

    return f"{iterations}${salt}${password_hash}"


def verify_password(password: str, stored_password_hash: str) -> bool:
    try:
        # Recupera os parâmetros usados no hash salvo para recalcular com a senha enviada.
        iterations_str, salt, saved_hash = stored_password_hash.split("$")
        iterations = int(iterations_str)

        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations
        ).hex()

        # Compara os hashes em tempo constante para reduzir risco de timing attack.
        return hmac.compare_digest(password_hash, saved_hash)
    except Exception:
        # Qualquer formato inválido ou erro no processo invalida a autenticação.
        return False
