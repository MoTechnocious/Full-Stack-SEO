"""JWT access tokens for the built-in dev IdP (HS256, symmetric secret from env)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.config import get_settings


def create_access_token(
    subject: str,
    *,
    email: str | None = None,
    name: str | None = None,
    org_id: str | None = None,
    role: str | None = None,
    ttl_minutes: int | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    ttl = ttl_minutes if ttl_minutes is not None else settings.access_token_ttl_minutes
    payload: dict[str, Any] = {
        "sub": subject,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ttl)).timestamp()),
    }
    if email:
        payload["email"] = email
    if name:
        payload["name"] = name
    if org_id:
        payload["org_id"] = org_id
    if role:
        payload["role"] = role
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Decode + validate a dev token. Raises ``jwt.PyJWTError`` on failure."""
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
