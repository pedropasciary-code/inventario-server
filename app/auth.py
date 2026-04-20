import hashlib
import hmac
import os
import secrets


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    iterations = 100_000

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations
    ).hex()

    return f"{iterations}${salt}${password_hash}"


def verify_password(password: str, stored_password_hash: str) -> bool:
    try:
        iterations_str, salt, saved_hash = stored_password_hash.split("$")
        iterations = int(iterations_str)

        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations
        ).hex()

        return hmac.compare_digest(password_hash, saved_hash)
    except Exception:
        return False