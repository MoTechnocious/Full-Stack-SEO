"""Typed job handlers wrapping the existing engines.

Each ``make_*_handler`` factory is called at submission time (inside the route,
where auth/RBAC/quota guards have already run) and captures fully-validated
inputs plus the injected provider/fetcher. Results are persisted through the
existing tenant-scoped repositories, so the existing GET endpoints keep working:

- crawl      -> ``result_ref`` is the crawl_id      (GET /audit/crawl/{id})
- rank poll  -> ``result_ref`` is ``domain|country`` (GET /rankings/{domain})
- report     -> ``result_ref`` is the report_id      (TenantRepos.get_report)

Workers must never reuse the request-scoped DB session (it is closed once the
response returns), so handlers receive a session *factory* bound to the same
engine instead.
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable

from sqlmodel import Session

from app.billing.usage import UsageService
from app.core.crawler.engine import Crawler
from app.core.crawler.fetcher import Fetcher
from app.core.keywords.providers import SerpProvider
from app.core.keywords.rank_tracker import RankTracker
from app.core.reporting.reports import build_report
from app.core.reporting.tasks import generate_action_plan
from app.core.reporting.whitelabel import apply_branding
from app.jobs.queue import JobHandler, ProgressFn
from app.models.audit import CrawlConfig
from app.models.common import Device
from app.services.store import InMemoryStore
from app.tenancy.repositories import get_repos

SessionFactory = Callable[[], Session]


def session_factory_from(session: Session) -> SessionFactory:
    """Return a factory producing fresh sessions on ``session``'s engine."""
    engine = session.get_bind()

    def factory() -> Session:
        return Session(engine)

    return factory


def make_crawl_handler(
    org_id: str,
    config: CrawlConfig,
    fetcher: Fetcher,
    session_factory: SessionFactory,
) -> JobHandler:
    """Full-site crawl via the existing crawler engine; persists the CrawlResult."""

    def handler(progress: ProgressFn) -> str:
        progress(5)
        result = asyncio.run(Crawler(fetcher, config).crawl())
        progress(80)
        with session_factory() as session:
            get_repos(session, org_id).save_crawl(result)
            UsageService(session).record(org_id, "crawls_per_month", 1)
        progress(100)
        return result.crawl_id

    return handler


def make_rank_poll_handler(
    org_id: str,
    domain: str,
    country: str,
    keywords: list[str],
    device: Device,
    search_volumes: dict[str, int],
    serp_provider: SerpProvider,
    session_factory: SessionFactory,
) -> JobHandler:
    """Rank poll via the existing RankTracker; persists the summary."""

    def handler(progress: ProgressFn) -> str:
        progress(5)
        tracker = RankTracker(store=InMemoryStore(), serp_provider=serp_provider)  # transient, per-job
        tracker.add_keywords(
            domain, country, keywords, device=device, search_volumes=search_volumes or None
        )
        progress(30)
        tracker.poll(domain, country, device=device)
        progress(70)
        summary = tracker.build_summary(domain, country)
        with session_factory() as session:
            get_repos(session, org_id).save_summary(summary)
        progress(100)
        return f"{domain}|{country}"

    return handler


def make_report_handler(
    org_id: str,
    site: str,
    period_start: str,
    period_end: str,
    branding: dict | None,
    crawl_id: str | None,
    domain: str | None,
    country: str,
    session_factory: SessionFactory,
) -> JobHandler:
    """Report build via the existing reporting engine; persists the Report.

    ``branding`` must already be feature-gated at submission time (routes pass
    None unless the plan has the ``white_label`` feature).
    """

    def handler(progress: ProgressFn) -> str:
        progress(5)
        with session_factory() as session:
            repos = get_repos(session, org_id)
            audit = repos.get_crawl(crawl_id) if crawl_id else None
            rank_summary = repos.get_summary(domain, country) if domain else None
            progress(30)
            plan = generate_action_plan(site, audit=audit, rank_summary=rank_summary)
            progress(60)
            report = build_report(
                site, period_start, period_end, branding=apply_branding(branding),
                audit=audit, rank_summary=rank_summary, action_plan=plan,
            )
            repos.save_report(report)
            UsageService(session).record(org_id, "reports_per_month", 1)
        progress(100)
        return report.report_id

    return handler
