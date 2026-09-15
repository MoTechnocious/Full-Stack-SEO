"""Immutable request-scoped tenant context, resolved by the auth dependencies."""
from __future__ import annotations

from dataclasses import dataclass, field

from app.tenancy.rbac import Role, has_permission, role_at_least


@dataclass
class TenantContext:
    user_id: str
    org_id: str
    org_name: str
    role: Role
    plan_code: str = "free"
    email: str | None = None
    auth_method: str = "token"       # "token" | "api_key"
    api_key_id: str | None = None
    scopes: list[str] = field(default_factory=list)

    def can(self, permission: str) -> bool:
        return has_permission(self.role, permission)

    def at_least(self, minimum: str | Role) -> bool:
        return role_at_least(self.role, minimum)
