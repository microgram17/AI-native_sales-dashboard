from __future__ import annotations

import jwt

from app.schemas.auth import VerifiedIdentity


class InvalidTokenError(Exception):
    """Raised when a token cannot be verified or is missing required claims."""


class JwtVerifier:
    """Verifies JWTs and returns a VerifiedIdentity.

    Knows nothing about FastAPI or HTTP; it only translates PyJWT errors into
    the application-level InvalidTokenError.
    """

    def __init__(
        self,
        *,
        secret: str,
        algorithm: str = "HS256",
        issuer: str | None = None,
        audience: str | None = None,
    ) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._issuer = issuer
        self._audience = audience

    def verify(self, token: str) -> VerifiedIdentity:
        options = {
            "require": ["exp"],
            "verify_aud": self._audience is not None,
        }
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                issuer=self._issuer,
                audience=self._audience,
                options=options,
            )
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(str(exc)) from exc

        subject = payload.get("sub")
        if not subject:
            raise InvalidTokenError("Token is missing a non-empty 'sub' claim")

        email = payload.get("email")
        return VerifiedIdentity(subject=subject, email=email)
