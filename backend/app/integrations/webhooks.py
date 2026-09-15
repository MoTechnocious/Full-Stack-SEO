"""Inbound webhook signature verification and event parsing.

Used to authenticate webhooks arriving from third parties (e.g. Make.com
callbacks, form providers) before they are trusted and processed.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone

from app.models.integrations import WebhookEvent


def sign_payload(secret: str, payload: bytes) -> str:
    """Return the hex-encoded HMAC-SHA256 signature of ``payload`` using ``secret``."""
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def verify_signature(secret: str, payload: bytes, signature: str) -> bool:
    """Constant-time verification of an HMAC-SHA256 hex signature.

    Returns False (never raises) when ``signature`` is empty/None or malformed.
    """
    if not signature:
        return False
    expected = sign_payload(secret, payload)
    try:
        return hmac.compare_digest(expected, signature)
    except TypeError:
        # Defensive: compare_digest requires str/bytes of matching type.
        return False


def _get_header(headers: dict[str, str], name: str) -> str | None:
    """Case-insensitive lookup into a headers mapping."""
    if name in headers:
        return headers[name]
    lower_name = name.lower()
    for key, value in headers.items():
        if key.lower() == lower_name:
            return value
    return None


def parse_event(
    secret: str,
    headers: dict[str, str],
    body: bytes,
    signature_header: str = "X-Signature",
) -> WebhookEvent:
    """Verify and parse an inbound webhook request into a `WebhookEvent`.

    Never raises: an invalid/missing signature yields ``verified=False`` and
    malformed JSON yields an empty payload — both are reported on the returned
    event rather than raised as exceptions.
    """
    signature = _get_header(headers, signature_header)
    verified = verify_signature(secret, body, signature or "")

    payload: dict[str, object] = {}
    if body:
        try:
            parsed = json.loads(body)
            if isinstance(parsed, dict):
                payload = parsed
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = {}

    event_type = str(payload.get("type", "unknown"))

    return WebhookEvent(
        id=uuid.uuid4().hex,
        type=event_type,
        payload=payload,
        signature=signature,
        verified=verified,
        received_at=datetime.now(timezone.utc),
    )
