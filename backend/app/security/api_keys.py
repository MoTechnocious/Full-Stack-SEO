"""API-key generation + hashing.

Only the SHA-256 hash of a key is stored (never the secret itself), the same way
passwords are stored. The full secret is shown to the user exactly once at creation.
"""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass


@dataclass
class GeneratedApiKey:
    secret: str      # full plaintext key — show once, never persist
    prefix: str
    last4: str
    hash: str        # SHA-256 hex — this is what gets stored


def hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def generate_api_key(prefix: str = "msk") -> GeneratedApiKey:
    body = secrets.token_urlsafe(32)
    secret = f"{prefix}_{body}"
    return GeneratedApiKey(
        secret=secret,
        prefix=prefix,
        last4=secret[-4:],
        hash=hash_secret(secret),
    )
