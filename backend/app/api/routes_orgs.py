"""Organization + membership/invite routes."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.billing.subscriptions import get_subscription
from app.db.models_tenancy import Invite, Membership, Organization, User
from app.db.session import get_session
from app.middleware.errors import BadRequestError, NotFoundError
from app.models.common import AppModel
from app.tenancy.context import TenantContext
from app.tenancy.deps import get_tenant_context, require_permission
from app.tenancy.provisioning import create_organization, get_membership, list_memberships

router = APIRouter(prefix="/orgs", tags=["organizations"])


class CreateOrgBody(AppModel):
    name: str


class InviteBody(AppModel):
    email: str
    role: str = "editor"


class AcceptBody(AppModel):
    token: str


@router.get("")
def list_orgs(ctx: TenantContext = Depends(get_tenant_context), session: Session = Depends(get_session)):
    out = []
    for m in list_memberships(session, ctx.user_id):
        o = session.get(Organization, m.org_id)
        if o:
            out.append({"id": o.id, "name": o.name, "slug": o.slug, "plan_code": o.plan_code, "role": m.role})
    return out


@router.post("")
def create_org(
    body: CreateOrgBody,
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
):
    user = session.get(User, ctx.user_id)
    if not user:
        raise BadRequestError("API-key sessions cannot create organizations.")
    org, m = create_organization(session, body.name, user)
    return {"id": org.id, "name": org.name, "slug": org.slug, "plan_code": org.plan_code, "role": m.role}


@router.get("/current")
def current(ctx: TenantContext = Depends(get_tenant_context), session: Session = Depends(get_session)):
    org = session.get(Organization, ctx.org_id)
    sub = get_subscription(session, ctx.org_id)
    return {
        "id": org.id,
        "name": org.name,
        "plan_code": org.plan_code,
        "role": ctx.role.value,
        "subscription": {"plan_code": sub.plan_code, "status": sub.status} if sub else None,
    }


@router.get("/members")
def members(ctx: TenantContext = Depends(get_tenant_context), session: Session = Depends(get_session)):
    rows = session.exec(select(Membership).where(Membership.org_id == ctx.org_id)).all()
    out = []
    for m in rows:
        u = session.get(User, m.user_id)
        out.append({"user_id": m.user_id, "email": u.email if u else None, "role": m.role, "status": m.status})
    return out


@router.post("/invites")
def create_invite(
    body: InviteBody,
    ctx: TenantContext = Depends(require_permission("members:manage")),
    session: Session = Depends(get_session),
):
    inv = Invite(
        org_id=ctx.org_id,
        email=body.email.lower(),
        role=body.role,
        invited_by=ctx.user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    session.add(inv)
    session.commit()
    session.refresh(inv)
    return {"id": inv.id, "email": inv.email, "role": inv.role, "token": inv.token, "expires_at": inv.expires_at}


@router.post("/invites/accept")
def accept_invite(
    body: AcceptBody,
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
):
    inv = session.exec(select(Invite).where(Invite.token == body.token, Invite.status == "pending")).first()
    if not inv:
        raise NotFoundError("Invite not found or already used.")
    if not get_membership(session, inv.org_id, ctx.user_id):
        session.add(Membership(org_id=inv.org_id, user_id=ctx.user_id, role=inv.role, status="active"))
    inv.status = "accepted"
    session.add(inv)
    session.commit()
    return {"org_id": inv.org_id, "role": inv.role}
