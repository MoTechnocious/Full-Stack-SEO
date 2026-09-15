"""Tenancy + identity tables: User, Organization, Membership, Invite, ApiKey.

Row-level multi-tenancy: every tenant-owned row carries ``org_id`` and access is
enforced in the repository/dependency layer.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel


def _uuid() -> str:
    return uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(default_factory=_uuid, primary_key=True)
    email: str = Field(index=True, unique=True)
    full_name: str = ""
    idp_provider: str = "dev"
    idp_subject: str | None = Field(default=None, index=True)
    password_hash: str | None = None  # only set for the built-in dev provider
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime = Field(default_factory=_now)


class Organization(SQLModel, table=True):
    __tablename__ = "organizations"

    id: str = Field(default_factory=_uuid, primary_key=True)
    name: str
    slug: str = Field(index=True, unique=True)
    plan_code: str = "free"
    billing_customer_id: str | None = None
    public_audit_token: str = Field(default_factory=_uuid, index=True)
    settings: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_now)


class Membership(SQLModel, table=True):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("org_id", "user_id", name="uq_membership_org_user"),)

    id: str = Field(default_factory=_uuid, primary_key=True)
    org_id: str = Field(index=True)
    user_id: str = Field(index=True)
    role: str = "owner"           # owner | agency_admin | editor | client
    status: str = "active"        # active | invited | suspended
    created_at: datetime = Field(default_factory=_now)


class Invite(SQLModel, table=True):
    __tablename__ = "invites"

    id: str = Field(default_factory=_uuid, primary_key=True)
    org_id: str = Field(index=True)
    email: str = Field(index=True)
    role: str = "editor"
    token: str = Field(default_factory=_uuid, index=True, unique=True)
    status: str = "pending"       # pending | accepted | revoked | expired
    invited_by: str | None = None
    created_at: datetime = Field(default_factory=_now)
    expires_at: datetime | None = None


class ApiKey(SQLModel, table=True):
    __tablename__ = "api_keys"

    id: str = Field(default_factory=_uuid, primary_key=True)
    org_id: str = Field(index=True)
    user_id: str | None = None
    name: str = "default"
    prefix: str = Field(index=True)
    last4: str = ""
    hash: str = Field(index=True, unique=True)  # SHA-256 hex of the full secret
    role: str = "editor"
    scopes: list = Field(default_factory=list, sa_column=Column(JSON))
    revoked: bool = False
    created_at: datetime = Field(default_factory=_now)
    last_used_at: datetime | None = None
