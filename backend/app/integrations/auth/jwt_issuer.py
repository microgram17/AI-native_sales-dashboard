from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt


class JwtIssuer:
    """Creates short-lived access tokens consumed by JwtVerifier."""

    def __init__(
        self,
        *,
        secret: str,
        algorithm: str = "HS256",
        issuer: str | None = None,
        audience: str | None = None,
        ttl_seconds: int = 3600,
    ) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._issuer = issuer
        self._audience = audience
        self._ttl_seconds = ttl_seconds

    @property
    def ttl_seconds(self) -> int:
        return self._ttl_seconds

    def issue(self, *, subject: str, email: str | None = None) -> str:
        now = datetime.now(tz=timezone.utc)
        payload: dict[str, object] = {
            "sub": subject,
            "iat": int(now.timestamp()),
            "exp": int(
                (now + timedelta(seconds=self._ttl_seconds)).timestamp()
            ),
        }

        if email:
            payload["email"] = email
        if self._issuer:
            payload["iss"] = self._issuer
        if self._audience:
            payload["aud"] = self._audience

        return jwt.encode(
            payload,
            self._secret,
            algorithm=self._algorithm,
        )
