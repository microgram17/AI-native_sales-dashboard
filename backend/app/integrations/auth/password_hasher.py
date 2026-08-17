from __future__ import annotations

from pwdlib import PasswordHash


class PasswordHasher:
    """Argon2-backed password hashing adapter."""

    def __init__(self) -> None:
        self._password_hash = PasswordHash.recommended()

    def hash(self, password: str) -> str:
        return self._password_hash.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            return self._password_hash.verify(password, password_hash)
        except Exception:
            # A malformed/unsupported stored hash is an authentication failure,
            # not a server error.
            return False
