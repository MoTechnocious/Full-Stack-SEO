"""Pluggable identity-provider layer (delegated authentication)."""
from app.idp.providers import (
    IdentityClaims,
    IdentityProvider,
    get_identity_provider,
)

__all__ = ["IdentityClaims", "IdentityProvider", "get_identity_provider"]
