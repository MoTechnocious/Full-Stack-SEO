"""Auth routes: dev signup/login, /me, org switching. External IdP handles its own login."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.billing.subscriptions import ensure_subscription
from app.config import Settings, get_settings
from app.db.models_tenancy import Organization, User
from app.db.session import get_session
from app.middleware.errors import BadRequestError, NotAuthenticatedError
from app.models.common import AppModel
from app.security.passwords import verify_password
from app.security.tokens import create_access_token
from app.tenancy.context import TenantContext
from app.tenancy.deps import get_tenant_context
from app.tenancy.provisioning import (
    create_local_user,
    create_organization,
    get_membership,
    get_user_by_email,
    list_memberships,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupBody(AppModel):
    email: str
    password: str
    full_name: str = ""
    org_name: str = ""


class LoginBody(AppModel):
    email: str
    password: str


class SwitchBody(AppModel):
    org_id: str


def _token(user: User, org: Organization, role: str) -> str:
    return create_access_token(user.id, email=user.email, name=user.full_name, org_id=org.id, role=role)


@router.post("/signup")
def signup(
    body: SignupBody,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    if settings.idp_provider != "dev":
        raise BadRequestError("Signup is handled by your identity provider.")
    if get_user_by_email(session, body.email):
        raise BadRequestError("An account with this email already exists.")
    user = create_local_user(session, body.email, body.password, body.full_name)
    name = body.org_name or f"{body.email.split('@')[0]} workspace"
    org, membership = create_organization(session, name, user)
    return {
        "access_token": _token(user, org, membership.role),
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email, "full_name": user.full_name},
        "org": {"id": org.id, "name": org.name, "plan_code": org.plan_code, "role": membership.role},
    }


@router.post("/login")
def login(
    body: LoginBody,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    if settings.idp_provider != "dev":
        raise BadRequestError("Login is handled by your identity provider.")
    user = get_user_by_email(session, body.email)
    if not user or not verify_password(body.password, user.password_hash):
        raise NotAuthenticatedError("Invalid email or password.")
    memberships = list_memberships(session, user.id)
    if not memberships:
        raise NotAuthenticatedError("This account has no organization membership.")
    m = memberships[0]
    org = session.get(Organization, m.org_id)
    ensure_subscription(session, org.id, org.plan_code)
    return {
        "access_token": _token(user, org, m.role),
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email},
        "org": {"id": org.id, "name": org.name, "role": m.role, "plan_code": org.plan_code},
        "memberships": [{"org_id": x.org_id, "role": x.role} for x in memberships],
    }


@router.get("/me")
def me(ctx: TenantContext = Depends(get_tenant_context)):
    return {
        "user_id": ctx.user_id,
        "email": ctx.email,
        "org_id": ctx.org_id,
        "org_name": ctx.org_name,
        "role": ctx.role.value,
        "plan_code": ctx.plan_code,
        "auth_method": ctx.auth_method,
    }


@router.post("/switch-org")
def switch_org(
    body: SwitchBody,
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
):
    membership = get_membership(session, body.org_id, ctx.user_id)
    if not membership:
        raise NotAuthenticatedError("You are not a member of that organization.")
    org = session.get(Organization, body.org_id)
    user = session.get(User, ctx.user_id)
    return {
        "access_token": _token(user, org, membership.role),
        "token_type": "bearer",
        "org": {"id": org.id, "name": org.name, "role": membership.role, "plan_code": org.plan_code},
    }
