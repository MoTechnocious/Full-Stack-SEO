"""Tenant-scoped persistence for SEO artifacts.

Engine outputs (rich Pydantic domain models) are stored as JSON payloads on
org-scoped rows; leads keep structured columns for querying. Every row carries
``org_id``.
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


class Project(SQLModel, table=True):
    __tablename__ = "projects"

    id: str = Field(default_factory=_uuid, primary_key=True)
    org_id: str = Field(index=True)
    name: str
    domain: str = Field(index=True)
    created_at: datetime = Field(default_factory=_now)
    settings: dict = Field(default_factory=dict, sa_column=Column(JSON))


class CrawlRecord(SQLModel, table=True):
    __tablename__ = "crawl_records"

    id: str = Field(primary_key=True)  # == CrawlResult.crawl_id
    org_id: str = Field(index=True)
    project_id: str | None = Field(default=None, index=True)
    start_url: str = ""
    created_at: datetime = Field(default_factory=_now)
    summary: dict = Field(default_factory=dict, sa_column=Column(JSON))
    data: dict = Field(default_factory=dict, sa_column=Column(JSON))


class RankingRecord(SQLModel, table=True):
    __tablename__ = "ranking_records"
    __table_args__ = (
        UniqueConstraint("org_id", "domain", "country", name="uq_ranking_org_domain_country"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    org_id: str = Field(index=True)
    project_id: str | None = Field(default=None, index=True)
    domain: str = Field(index=True)
    country: str = Field(default="us", index=True)
    data: dict = Field(default_factory=dict, sa_column=Column(JSON))
    updated_at: datetime = Field(default_factory=_now)


class ReportRecord(SQLModel, table=True):
    __tablename__ = "report_records"

    id: str = Field(primary_key=True)  # == Report.report_id
    org_id: str = Field(index=True)
    project_id: str | None = Field(default=None, index=True)
    site: str = ""
    data: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_now)


class ActionPlanRecord(SQLModel, table=True):
    __tablename__ = "action_plan_records"

    id: str = Field(default_factory=_uuid, primary_key=True)
    org_id: str = Field(index=True)
    site: str = Field(index=True)
    data: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_now)


class LeadRow(SQLModel, table=True):
    __tablename__ = "leads"

    id: str = Field(default_factory=_uuid, primary_key=True)
    org_id: str = Field(index=True)
    project_id: str | None = Field(default=None, index=True)
    name: str = ""
    email: str = Field(default="", index=True)
    phone: str | None = None
    company: str | None = None
    website: str | None = None
    source: str = "mini_audit"
    status: str = "pending"
    data: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_now)


class DeliveryLogRow(SQLModel, table=True):
    __tablename__ = "delivery_logs"

    id: str = Field(primary_key=True)
    org_id: str = Field(index=True)
    lead_id: str | None = Field(default=None, index=True)
    target: str = ""
    status: str = "pending"
    attempts: int = 0
    last_error: str | None = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
