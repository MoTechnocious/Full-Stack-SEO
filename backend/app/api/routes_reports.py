"""Reporting routes — tenant-scoped; white-label branding gated by plan feature."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from app.billing.deps import require_quota
from app.billing.entitlements import has_feature
from app.billing.usage import UsageService
from app.core.reporting.reports import build_report, render_report_html
from app.core.reporting.tasks import generate_action_plan
from app.core.reporting.whitelabel import apply_branding
from app.db.session import get_session
from app.models.common import AppModel
from app.models.reporting import ActionPlan
from app.tenancy.context import TenantContext
from app.tenancy.deps import require_permission
from app.tenancy.repositories import get_repos

router = APIRouter(prefix="/reports", tags=["reports"])


class ActionPlanBody(AppModel):
    site: str
    crawl_id: str | None = None
    domain: str | None = None
    country: str = "us"


@router.post("/action-plan", response_model=ActionPlan)
async def action_plan_route(
    body: ActionPlanBody,
    ctx: TenantContext = Depends(require_permission("seo:read")),
    session: Session = Depends(get_session),
) -> ActionPlan:
    repos = get_repos(session, ctx.org_id)
    audit = repos.get_crawl(body.crawl_id) if body.crawl_id else None
    rank_summary = repos.get_summary(body.domain, body.country) if body.domain else None
    plan = generate_action_plan(body.site, audit=audit, rank_summary=rank_summary)
    repos.save_action_plan(plan)
    return plan


class ReportBody(AppModel):
    site: str
    period_start: str
    period_end: str
    branding: dict | None = None
    crawl_id: str | None = None
    domain: str | None = None
    country: str = "us"


@router.post("/build", dependencies=[Depends(require_permission("seo:write"))])
async def build_report_route(
    body: ReportBody,
    format: str = Query("json", pattern="^(json|html)$"),
    ctx: TenantContext = Depends(require_quota("reports_per_month")),
    session: Session = Depends(get_session),
):
    repos = get_repos(session, ctx.org_id)
    audit = repos.get_crawl(body.crawl_id) if body.crawl_id else None
    rank_summary = repos.get_summary(body.domain, body.country) if body.domain else None
    # White-label branding requires the plan feature; otherwise fall back to default.
    branding_input = body.branding if (body.branding and has_feature(ctx.plan_code, "white_label")) else None
    branding = apply_branding(branding_input)
    plan = generate_action_plan(body.site, audit=audit, rank_summary=rank_summary)
    report = build_report(
        body.site, body.period_start, body.period_end, branding=branding,
        audit=audit, rank_summary=rank_summary, action_plan=plan,
    )
    repos.save_report(report)
    UsageService(session).record(ctx.org_id, "reports_per_month", 1)
    if format == "html":
        return HTMLResponse(content=render_report_html(report))
    return report
