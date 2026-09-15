"""FastAPI auth dependencies.

Resolves a :class:`TenantContext` from either an ``X-API-Key`` header (self-hosted
hashed key) or an ``Authorization: Bearer`` token (verified by the configured IdP,
with JIT user provisioning). Also exposes role/permission guards.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from fastapi import Depends, Request
from sqlmodel import Session, select

from app.db.models_tenancy import ApiKey, Organization
from app.db.session import get_session
from app.idp import get_identity_provider
from app.middleware.errors import ForbiddenError, NotAuthenticatedError
from app.security.api_keys import hash_secret
from app.tenancy.context import TenantContext
from app.tenancy.provisioning import provision_from_claims, resolve_active_org
from app.tenancy.rbac import Role, has_permission, normalize_role, role_at_least


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return None


def _context_from_api_key(session: Session, raw_key: str) -> TenantContext:
    row = session.exec(
        select(ApiKey).where(ApiKey.hash == hash_secret(raw_key), ApiKey.revoked == False)  # noqa: E712
    ).first()
    if row is None:
        raise NotAuthenticatedError("Invalid or revoked API key.")
    org = session.get(Organization, row.org_id)
    if org is None:
        raise NotAuthenticatedError("API key organization not found.")
    row.last_used_at = datetime.now(timezone.utc)
    session.add(row)
    session.commit()
    return TenantContext(
        user_id=row.user_id or f"apikey:{row.id}",
        org_id=org.id,
        org_name=org.name,
        role=normalize_role(row.role),
        plan_code=org.plan_code,
        email=None,
        auth_method="api_key",
        api_key_id=row.id,
        scopes=list(row.scopes or []),
    )


def _context_from_token(session: Session, request: Request, token: str) -> TenantContext:
    try:
        claims = get_identity_provider().verify_token(token)
    except NotImplementedError:
        raise  # provider misconfiguration -> surfaces as 500 (ops error, not auth error)
    except Exception as exc:  # invalid/expired token
        raise NotAuthenticatedError("Invalid or expired token.") from exc

    user = provision_from_claims(session, claims)
    requested_org = claims.org_id or request.headers.get("X-Org-Id")
    resolved = resolve_active_org(session, user, requested_org)
    if resolved is None:
        raise ForbiddenError("This user has no active organization membership.")
    org, membership = resolved
    return TenantContext(
        user_id=user.id,
        org_id=org.id,
        org_name=org.name,
        role=normalize_role(membership.role),  # DB membership is authoritative
        plan_code=org.plan_code,
        email=user.email,
        auth_method="token",
    )


def get_tenant_context(
    request: Request, session: Session = Depends(get_session)
) -> TenantContext:
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return _context_from_api_key(session, api_key)
    token = _bearer_token(request)
    if token:
        return _context_from_token(session, request, token)
    raise NotAuthenticatedError("Authentication required.")


def require_permission(permission: str) -> Callable[..., TenantContext]:
    def dependency(ctx: TenantContext = Depends(get_tenant_context)) -> TenantContext:
        if not has_permission(ctx.role, permission):
            raise ForbiddenError(f"Your role '{ctx.role.value}' lacks permission '{permission}'.")
        return ctx

    return dependency


def require_min_role(minimum: str | Role) -> Callable[..., TenantContext]:
    def dependency(ctx: TenantContext = Depends(get_tenant_context)) -> TenantContext:
        if not role_at_least(ctx.role, minimum):
            raise ForbiddenError(f"Requires at least '{normalize_role(minimum).value}' role.")
        return ctx

    return dependency
