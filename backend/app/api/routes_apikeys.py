"""API-key management routes (self-hosted, SHA-256 hashed)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.config import get_settings
from app.db.models_tenancy import ApiKey
from app.db.session import get_session
from app.middleware.errors import NotFoundError
from app.models.common import AppModel
from app.security.api_keys import generate_api_key
from app.tenancy.context import TenantContext
from app.tenancy.deps import get_tenant_context, require_permission

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


class CreateKeyBody(AppModel):
    name: str = "default"
    role: str = "editor"


@router.get("")
def list_keys(ctx: TenantContext = Depends(get_tenant_context), session: Session = Depends(get_session)):
    keys = session.exec(select(ApiKey).where(ApiKey.org_id == ctx.org_id)).all()
    return [
        {
            "id": k.id, "name": k.name, "prefix": k.prefix, "last4": k.last4, "role": k.role,
            "revoked": k.revoked, "created_at": k.created_at, "last_used_at": k.last_used_at,
        }
        for k in keys
    ]


@router.post("")
def create_key(
    body: CreateKeyBody,
    ctx: TenantContext = Depends(require_permission("apikeys:manage")),
    session: Session = Depends(get_session),
):
    gen = generate_api_key(get_settings().api_key_prefix)
    k = ApiKey(
        org_id=ctx.org_id, user_id=ctx.user_id, name=body.name,
        prefix=gen.prefix, last4=gen.last4, hash=gen.hash, role=body.role,
    )
    session.add(k)
    session.commit()
    session.refresh(k)
    return {
        "id": k.id, "name": k.name, "secret": gen.secret, "prefix": k.prefix, "last4": k.last4,
        "role": k.role, "note": "Store this secret now; it will not be shown again.",
    }


@router.delete("/{key_id}")
def revoke_key(
    key_id: str,
    ctx: TenantContext = Depends(require_permission("apikeys:manage")),
    session: Session = Depends(get_session),
):
    k = session.get(ApiKey, key_id)
    if not k or k.org_id != ctx.org_id:
        raise NotFoundError("API key not found.")
    k.revoked = True
    session.add(k)
    session.commit()
    return {"id": k.id, "revoked": True}
