"""Create a short-lived development JWT for local testing.

Usage:
    uv run python scripts/create_dev_token.py

Prints only the token followed by an example usage command.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt

# Allow running as a plain script (python scripts/create_dev_token.py) by
# putting the backend root on sys.path so `app` is importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings

TOKEN_LIFETIME = timedelta(hours=1)


def create_token() -> str:
    settings = get_settings()
    now = datetime.now(tz=timezone.utc)
    payload: dict[str, object] = {
        "sub": "dev-user",
        "email": "dev@example.com",
        "iat": int(now.timestamp()),
        "exp": int((now + TOKEN_LIFETIME).timestamp()),
    }
    if settings.jwt_issuer:
        payload["iss"] = settings.jwt_issuer
    if settings.jwt_audience:
        payload["aud"] = settings.jwt_audience

    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def main() -> None:
    token = create_token()
    print(token)
    print()
    print("Example (PowerShell):")
    print(
        '  Invoke-RestMethod -Uri http://localhost:8000/auth/me '
        f'-Headers @{{ Authorization = "Bearer {token}" }}'
    )


if __name__ == "__main__":
    main()
