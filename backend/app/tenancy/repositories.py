"""Tenant-scoped persistence.

Every method is bound to a single ``org_id`` and refuses to read/write rows that
belong to another tenant. Rich engine outputs are round-tripped through JSON
columns; the Pydantic domain models remain the source of truth.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session, select

from app.db.models_seo import (
    ActionPlanRecord,
    CrawlRecord,
    DeliveryLogRow,
    LeadRow,
    Project,
    RankingRecord,
    ReportRecord,
)
from app.models.audit import CrawlResult
from app.models.integrations import DeliveryLog, LeadRecord
from app.models.keywords import RankTrackingSummary
from app.models.reporting import ActionPlan, Report


class TenantRepos:
    def __init__(self, session: Session, org_id: str):
        self.s = session
        self.org_id = org_id

    # ---- Projects / sites ----
    def create_project(self, name: str, domain: str) -> Project:
        project = Project(org_id=self.org_id, name=name, domain=domain)
        self.s.add(project)
        self.s.commit()
        self.s.refresh(project)
        return project

    def list_projects(self) -> list[Project]:
        return list(
            self.s.exec(select(Project).where(Project.org_id == self.org_id)).all()
        )

    def get_project(self, project_id: str) -> Project | None:
        row = self.s.get(Project, project_id)
        return row if row and row.org_id == self.org_id else None

    def count_projects(self) -> int:
        return len(self.list_projects())

    # ---- Crawls ----
    def save_crawl(self, crawl: CrawlResult, project_id: str | None = None) -> CrawlResult:
        self.s.merge(
            CrawlRecord(
                id=crawl.crawl_id,
                org_id=self.org_id,
                project_id=project_id,
                start_url=crawl.start_url,
                summary=crawl.summary.model_dump(mode="json"),
                data=crawl.model_dump(mode="json"),
            )
        )
        self.s.commit()
        return crawl

    def get_crawl(self, crawl_id: str) -> CrawlResult | None:
        row = self.s.get(CrawlRecord, crawl_id)
        if row is None or row.org_id != self.org_id:
            return None
        return CrawlResult.model_validate(row.data)

    def list_crawls(self) -> list[dict]:
        rows = self.s.exec(
            select(CrawlRecord).where(CrawlRecord.org_id == self.org_id)
        ).all()
        return [
            {"crawl_id": r.id, "start_url": r.start_url, "created_at": r.created_at, "summary": r.summary}
            for r in rows
        ]

    # ---- Rankings ----
    def save_summary(self, summary: RankTrackingSummary, project_id: str | None = None) -> None:
        existing = self.s.exec(
            select(RankingRecord).where(
                RankingRecord.org_id == self.org_id,
                RankingRecord.domain == summary.domain,
                RankingRecord.country == summary.country,
            )
        ).first()
        payload = summary.model_dump(mode="json")
        if existing:
            existing.data = payload
            existing.updated_at = datetime.now(timezone.utc)
            self.s.add(existing)
        else:
            self.s.add(
                RankingRecord(
                    org_id=self.org_id,
                    project_id=project_id,
                    domain=summary.domain,
                    country=summary.country,
                    data=payload,
                )
            )
        self.s.commit()

    def get_summary(self, domain: str, country: str) -> RankTrackingSummary | None:
        row = self.s.exec(
            select(RankingRecord).where(
                RankingRecord.org_id == self.org_id,
                RankingRecord.domain == domain,
                RankingRecord.country == country,
            )
        ).first()
        return RankTrackingSummary.model_validate(row.data) if row else None

    def count_tracked_keywords(self) -> int:
        rows = self.s.exec(
            select(RankingRecord).where(RankingRecord.org_id == self.org_id)
        ).all()
        return sum(len(RankTrackingSummary.model_validate(r.data).keywords) for r in rows)

    # ---- Reports / action plans ----
    def save_report(self, report: Report, project_id: str | None = None) -> Report:
        self.s.merge(
            ReportRecord(
                id=report.report_id,
                org_id=self.org_id,
                project_id=project_id,
                site=report.site,
                data=report.model_dump(mode="json"),
            )
        )
        self.s.commit()
        return report

    def get_report(self, report_id: str) -> Report | None:
        row = self.s.get(ReportRecord, report_id)
        if row is None or row.org_id != self.org_id:
            return None
        return Report.model_validate(row.data)

    def save_action_plan(self, plan: ActionPlan) -> ActionPlanRecord:
        record = ActionPlanRecord(
            org_id=self.org_id, site=plan.site, data=plan.model_dump(mode="json")
        )
        self.s.add(record)
        self.s.commit()
        self.s.refresh(record)
        return record

    # ---- Leads / deliveries ----
    def save_lead(self, lead: LeadRecord, project_id: str | None = None) -> LeadRow:
        row = LeadRow(
            id=lead.id or None,  # LeadRow generates a uuid if None
            org_id=self.org_id,
            project_id=project_id,
            name=lead.name,
            email=lead.email,
            phone=lead.phone,
            company=lead.company,
            website=lead.website,
            source=lead.source,
            data=lead.model_dump(mode="json"),
        ) if lead.id else LeadRow(
            org_id=self.org_id,
            project_id=project_id,
            name=lead.name,
            email=lead.email,
            phone=lead.phone,
            company=lead.company,
            website=lead.website,
            source=lead.source,
            data=lead.model_dump(mode="json"),
        )
        self.s.add(row)
        self.s.commit()
        self.s.refresh(row)
        return row

    def list_leads(self) -> list[LeadRow]:
        return list(self.s.exec(select(LeadRow).where(LeadRow.org_id == self.org_id)).all())

    def save_delivery(self, log: DeliveryLog) -> None:
        self.s.merge(
            DeliveryLogRow(
                id=log.id,
                org_id=self.org_id,
                lead_id=log.lead_id,
                target=log.target,
                status=log.status.value if hasattr(log.status, "value") else str(log.status),
                attempts=log.attempts,
                last_error=log.last_error,
                created_at=log.created_at,
                updated_at=log.updated_at,
            )
        )
        self.s.commit()

    def list_deliveries(self) -> list[DeliveryLog]:
        rows = self.s.exec(
            select(DeliveryLogRow).where(DeliveryLogRow.org_id == self.org_id)
        ).all()
        out: list[DeliveryLog] = []
        for r in rows:
            out.append(
                DeliveryLog(
                    id=r.id,
                    target=r.target,
                    lead_id=r.lead_id,
                    status=r.status,
                    attempts=r.attempts,
                    last_error=r.last_error,
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                )
            )
        return out


def get_repos(session: Session, org_id: str) -> TenantRepos:
    return TenantRepos(session, org_id)
