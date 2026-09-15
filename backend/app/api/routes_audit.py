"""Crawl / audit routes — tenant-scoped, quota-enforced."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlmodel import Session

from app.api.deps import get_fetcher, get_settings_dep
from app.billing.deps import require_quota
from app.billing.entitlements import get_limit
from app.billing.usage import UsageService
from app.config import Settings
from app.core.crawler.analyzers import analyze_page
from app.core.crawler.engine import Crawler, audit_single
from app.core.crawler.fetcher import FetchResponse, Fetcher
from app.core.crawler.sitemap import generate_sitemap
from app.db.session import get_session
from app.middleware.errors import BadRequestError, NotFoundError
from app.models.audit import CrawlConfig, CrawlResult, PageAuditResult
from app.models.common import AppModel
from app.tenancy.context import TenantContext
from app.tenancy.deps import require_permission
from app.tenancy.repositories import get_repos

router = APIRouter(prefix="/audit", tags=["audit"])


class PageAuditRequest(AppModel):
    url: str | None = None
    html: str | None = None


class SitemapRequest(AppModel):
    urls: list[str] = []


@router.post("/page", response_model=PageAuditResult)
async def audit_page_route(
    body: PageAuditRequest,
    ctx: TenantContext = Depends(require_permission("seo:run")),
    fetcher: Fetcher = Depends(get_fetcher),
    settings: Settings = Depends(get_settings_dep),
) -> PageAuditResult:
    if not body.url and not body.html:
        raise BadRequestError("Provide either 'url' or 'html'.")
    url = body.url or "https://input.local/"
    config = CrawlConfig(start_url=url, user_agent=settings.crawler_user_agent)
    if body.html is not None:
        resp = FetchResponse(
            url=url, final_url=url, status_code=200,
            headers={"content-type": "text/html"}, text=body.html,
            elapsed_ms=0, content_type="text/html",
        )
        return analyze_page(url, resp, root_url=url, config=config)
    return await audit_single(url, fetcher, config)


@router.post("/crawl", response_model=CrawlResult, dependencies=[Depends(require_permission("seo:run"))])
async def run_crawl_route(
    config: CrawlConfig,
    ctx: TenantContext = Depends(require_quota("crawls_per_month")),
    fetcher: Fetcher = Depends(get_fetcher),
    session: Session = Depends(get_session),
) -> CrawlResult:
    page_cap = get_limit(ctx.plan_code, "pages_per_crawl")
    if page_cap and page_cap > 0:
        config.max_pages = min(config.max_pages, page_cap)
    result = await Crawler(fetcher, config).crawl()
    get_repos(session, ctx.org_id).save_crawl(result)
    UsageService(session).record(ctx.org_id, "crawls_per_month", 1)
    return result


@router.get("/crawl/{crawl_id}", response_model=CrawlResult)
async def get_crawl_route(
    crawl_id: str,
    ctx: TenantContext = Depends(require_permission("seo:read")),
    session: Session = Depends(get_session),
) -> CrawlResult:
    crawl = get_repos(session, ctx.org_id).get_crawl(crawl_id)
    if crawl is None:
        raise NotFoundError(f"Crawl '{crawl_id}' not found.")
    return crawl


@router.post("/sitemap")
async def sitemap_route(
    body: SitemapRequest,
    ctx: TenantContext = Depends(require_permission("seo:read")),
) -> Response:
    return Response(content=generate_sitemap(body.urls), media_type="application/xml")
