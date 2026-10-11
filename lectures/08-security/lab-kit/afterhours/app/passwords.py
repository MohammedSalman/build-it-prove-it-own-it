"""Storing passwords: a salted, deliberately slow hash, never the password itself."""

import base64
import hashlib
import hmac
import secrets

# scrypt settings: slow enough to make guessing expensive, fast enough for a login (~30 ms).
_SCRYPT = {"n": 2**14, "r": 8, "p": 1, "dklen": 32}


def hash_password(password: str, salt: bytes | None = None) -> str:
    """A salted scrypt hash, stored as "salt$hash" in base64."""
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def matches(password: str, stored: str | None) -> bool:
    """Does `password` match the stored hash? An account with no hash never matches."""
    if not stored:
        return False
    salt_b64, digest_b64 = stored.split("$")
    expected = hash_password(password, base64.b64decode(salt_b64)).split("$")[1]
    return hmac.compare_digest(expected, digest_b64)       # takes the same time either way
