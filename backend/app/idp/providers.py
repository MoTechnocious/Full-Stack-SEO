"""Identity providers.

Authentication is *delegated*: the backend verifies a bearer token and maps it to
a local user (just-in-time provisioning). The built-in ``dev`` provider verifies
our own HS256 tokens so the whole app runs with zero third-party dependencies;
``clerk``/``supabase``/``auth0`` verify the vendor's RS256 JWTs via JWKS.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

import jwt

from app.config import Settings, get_settings
from app.security.tokens import decode_token


@dataclass
class IdentityClaims:
    subject: str
    email: str | None = None
    name: str | None = None
    provider: str = "dev"
    org_id: str | None = None
    role: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class IdentityProvider(Protocol):
    name: str

    def verify_token(self, token: str) -> IdentityClaims: ...


class DevIdentityProvider:
    """Verifies tokens minted by this app's own ``/auth`` endpoints."""

    name = "dev"

    def verify_token(self, token: str) -> IdentityClaims:
        payload = decode_token(token)  # raises jwt.PyJWTError if invalid/expired
        return IdentityClaims(
            subject=str(payload.get("sub", "")),
            email=payload.get("email"),
            name=payload.get("name"),
            provider="dev",
            org_id=payload.get("org_id"),
            role=payload.get("role"),
            raw=payload,
        )


class ExternalJwksProvider:
    """Verifies a third-party IdP's RS256 JWT using its JWKS endpoint."""

    def __init__(self, name: str, jwks_url: str | None, issuer: str | None, audience: str | None):
        self.name = name
        self.jwks_url = jwks_url
        self.issuer = issuer
        self.audience = audience

    def verify_token(self, token: str) -> IdentityClaims:
        if not self.jwks_url:
            raise NotImplementedError(
                f"IdP '{self.name}' requires SEO_IDP_JWKS_URL (and optionally "
                "SEO_IDP_ISSUER / SEO_IDP_AUDIENCE) to be configured."
            )
        signing_key = jwt.PyJWKClient(self.jwks_url).get_signing_key_from_jwt(token).key
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=self.audience,
            issuer=self.issuer,
            options={"verify_aud": self.audience is not None},
        )
        return IdentityClaims(
            subject=str(payload.get("sub", "")),
            email=payload.get("email"),
            name=payload.get("name") or payload.get("given_name"),
            provider=self.name,
            raw=payload,
        )


def get_identity_provider(settings: Settings | None = None) -> IdentityProvider:
    settings = settings or get_settings()
    provider = settings.idp_provider.lower()
    if provider == "dev":
        return DevIdentityProvider()
    return ExternalJwksProvider(
        provider, settings.idp_jwks_url, settings.idp_issuer, settings.idp_audience
    )
