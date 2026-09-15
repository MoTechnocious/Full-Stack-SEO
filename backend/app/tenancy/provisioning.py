"""User/org provisioning: JIT user creation from IdP claims, org + owner setup."""
from __future__ import annotations

import re
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.config import get_settings
from app.db.models_tenancy import Membership, Organization, User
from app.idp.providers import IdentityClaims
from app.security.passwords import hash_password


def slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return base or "org"


def unique_slug(session: Session, name: str) -> str:
    base = slugify(name)
    slug = base
    i = 2
    while session.exec(select(Organization).where(Organization.slug == slug)).first():
        slug = f"{base}-{i}"
        i += 1
    return slug


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.exec(select(User).where(User.email == email.lower())).first()


def create_local_user(session: Session, email: str, password: str, full_name: str = "") -> User:
    """Create a user with a local (dev-IdP) password."""
    user = User(
        email=email.lower(),
        full_name=full_name,
        idp_provider="dev",
        password_hash=hash_password(password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def provision_from_claims(session: Session, claims: IdentityClaims) -> User:
    """Find or just-in-time create a user for a verified external identity."""
    user: User | None = None
    if claims.subject:
        user = session.exec(
            select(User).where(
                User.idp_subject == claims.subject, User.idp_provider == claims.provider
            )
        ).first()
    if user is None and claims.email:
        user = get_user_by_email(session, claims.email)
    if user is None:
        user = User(
            email=(claims.email or f"{claims.subject}@{claims.provider}.local").lower(),
            full_name=claims.name or "",
            idp_provider=claims.provider,
            idp_subject=claims.subject,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def create_organization(
    session: Session, name: str, owner: User, plan_code: str | None = None
) -> tuple[Organization, Membership]:
    settings = get_settings()
    org = Organization(
        name=name,
        slug=unique_slug(session, name),
        plan_code=plan_code or settings.default_plan_code,
    )
    session.add(org)
    session.commit()
    session.refresh(org)

    membership = Membership(org_id=org.id, user_id=owner.id, role="owner", status="active")
    session.add(membership)
    session.commit()
    session.refresh(membership)

    # Provision a subscription for the org (lazy import avoids a package cycle).
    from app.billing.subscriptions import ensure_subscription

    ensure_subscription(session, org.id, org.plan_code)
    return org, membership


def get_membership(session: Session, org_id: str, user_id: str) -> Membership | None:
    return session.exec(
        select(Membership).where(
            Membership.org_id == org_id, Membership.user_id == user_id
        )
    ).first()


def list_memberships(session: Session, user_id: str) -> list[Membership]:
    return list(
        session.exec(
            select(Membership).where(
                Membership.user_id == user_id, Membership.status == "active"
            )
        ).all()
    )


def resolve_active_org(
    session: Session, user: User, requested_org_id: str | None = None
) -> tuple[Organization, Membership] | None:
    memberships = list_memberships(session, user.id)
    if not memberships:
        return None
    chosen: Membership | None = None
    if requested_org_id:
        chosen = next((m for m in memberships if m.org_id == requested_org_id), None)
    if chosen is None:
        chosen = memberships[0]
    org = session.get(Organization, chosen.org_id)
    if org is None:
        return None
    return org, chosen


def touch(dt: datetime | None = None) -> datetime:
    return dt or datetime.now(timezone.utc)
