"""Lead data-integrity validation and normalization.

Pure, deterministic, and side-effect free: `validate_lead` never raises and never
performs network/database I/O. Callers (e.g. the CRM pipeline) decide what to do
with the resulting `LeadValidationResult`.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from app.models.integrations import LeadRecord, LeadValidationResult

# A pragmatic (not RFC-5322-exhaustive) email pattern: local-part@domain.tld
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

# Keep only digits and a leading/embedded '+' when normalizing phone numbers.
_PHONE_STRIP_RE = re.compile(r"[^\d+]")

# Detects an existing URL scheme, e.g. "https://", "http://", "ftp://".
_URL_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*://")


def _normalize_phone(raw: str) -> str:
    """Strip everything except digits and '+' signs from a phone number."""
    return _PHONE_STRIP_RE.sub("", raw)


def _normalize_website(raw: str) -> str:
    """Ensure a website URL has a scheme, defaulting to ``https://`` when absent."""
    site = raw.strip()
    if not site:
        return site
    if _URL_SCHEME_RE.match(site):
        return site
    return f"https://{site}"


def validate_lead(lead: LeadRecord) -> LeadValidationResult:
    """Validate + normalize a captured lead.

    Rules:
      - ``name`` is required (non-empty after trimming).
      - ``email`` is required and must match ``EMAIL_RE``.
      - ``phone`` is optional; when present it is normalized to digits/``+`` only.
      - ``website`` is optional; when present a missing scheme defaults to ``https://``.
      - Missing ``company`` produces a warning (non-fatal).

    Always returns a normalized copy of the lead (UTC ``created_at`` filled in,
    ``id`` assigned via ``uuid4().hex`` when missing) regardless of validity, so
    downstream callers always have a stable identifier to log against.

    Never raises.
    """
    errors: list[str] = []
    warnings: list[str] = []

    name = (lead.name or "").strip()
    if not name:
        errors.append("name is required")

    email = (lead.email or "").strip()
    if not email:
        errors.append("email is required")
    elif not EMAIL_RE.match(email):
        errors.append("email is invalid")

    phone: str | None = lead.phone.strip() if lead.phone else None
    if phone:
        normalized_phone = _normalize_phone(phone)
        if not normalized_phone:
            warnings.append("phone could not be normalized to a valid number; ignored")
            phone = None
        else:
            phone = normalized_phone

    website: str | None = lead.website.strip() if lead.website else None
    if website:
        website = _normalize_website(website)

    if not (lead.company or "").strip():
        warnings.append("company is missing")

    valid = not errors

    normalized = lead.model_copy(
        update={
            "id": lead.id or uuid.uuid4().hex,
            "name": name,
            "email": email,
            "phone": phone,
            "website": website,
            "created_at": lead.created_at or datetime.now(timezone.utc),
        }
    )

    return LeadValidationResult(valid=valid, normalized=normalized, errors=errors, warnings=warnings)
