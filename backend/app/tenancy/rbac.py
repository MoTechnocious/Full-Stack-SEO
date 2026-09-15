"""Application-owned RBAC.

Roles (ascending privilege): CLIENT (read-only) < EDITOR < AGENCY_ADMIN < OWNER.
Permission checks run in the backend (not the IdP), so resource-level rules like
"can this member edit this project" live here.
"""
from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    OWNER = "owner"
    AGENCY_ADMIN = "agency_admin"
    EDITOR = "editor"
    CLIENT = "client"


_RANK: dict[Role, int] = {
    Role.CLIENT: 1,
    Role.EDITOR: 2,
    Role.AGENCY_ADMIN: 3,
    Role.OWNER: 4,
}

# Permissions granted per role (OWNER implicitly has all).
_PERMISSIONS: dict[Role, set[str]] = {
    Role.CLIENT: {"projects:read", "seo:read", "reports:read", "leads:read"},
    Role.EDITOR: {
        "projects:read", "seo:read", "seo:run", "seo:write",
        "reports:read", "reports:write", "leads:read", "leads:write",
    },
    Role.AGENCY_ADMIN: {
        "projects:read", "projects:write", "members:manage", "apikeys:manage",
        "seo:read", "seo:run", "seo:write", "reports:read", "reports:write",
        "leads:read", "leads:write",
    },
    Role.OWNER: {"*"},
}


def normalize_role(value: str | Role | None) -> Role:
    if isinstance(value, Role):
        return value
    try:
        return Role(str(value))
    except ValueError:
        return Role.CLIENT


def role_rank(role: str | Role) -> int:
    return _RANK.get(normalize_role(role), 0)


def role_at_least(role: str | Role, minimum: str | Role) -> bool:
    return role_rank(role) >= role_rank(minimum)


def has_permission(role: str | Role, permission: str) -> bool:
    r = normalize_role(role)
    perms = _PERMISSIONS.get(r, set())
    return "*" in perms or permission in perms
