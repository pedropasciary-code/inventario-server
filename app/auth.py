import hashlib
import hmac

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

_ph = PasswordHasher()


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    # Legacy PBKDF2 hashes: "iterations$salt$hexhash"
    if stored_hash.startswith("$argon2"):
        return _verify_argon2(password, stored_hash)
    return _verify_pbkdf2(password, stored_hash)


def _verify_argon2(password: str, stored_hash: str) -> bool:
    try:
        return _ph.verify(stored_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def _verify_pbkdf2(password: str, stored_hash: str) -> bool:
    try:
        iterations_str, salt, saved_hash = stored_hash.split("$")
        iterations = int(iterations_str)
        computed = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        ).hex()
        return hmac.compare_digest(computed, saved_hash)
    except Exception:
        return False
