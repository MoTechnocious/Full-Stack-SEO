"""Models for the crawl/audit engine (Screaming Frog-style technical SEO)."""
from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.models.common import AppModel, Indexability, Issue


class CrawlConfig(AppModel):
    """Configuration controlling a crawl run."""

    start_url: str
    max_pages: int = Field(default=100, ge=1, le=100_000)
    max_depth: int = Field(default=5, ge=0, le=50)
    respect_robots: bool = True
    follow_external: bool = False
    render_js: bool = False  # informational flag; real rendering handled by fetcher impl
    user_agent: str = "MySEOappBot/0.1 (+https://scalingfirm.com/bot)"
    include_patterns: list[str] = []
    exclude_patterns: list[str] = []


class RedirectHop(AppModel):
    url: str
    status_code: int
    location: str | None = None


class LinkInfo(AppModel):
    source_url: str
    target_url: str
    anchor_text: str = ""
    rel: str = ""
    is_internal: bool = True
    status_code: int | None = None


class ImageInfo(AppModel):
    src: str
    alt: str | None = None
    has_alt: bool = False


class HreflangEntry(AppModel):
    lang: str
    href: str


class PageAuditResult(AppModel):
    """Everything discovered and derived for a single crawled URL."""

    url: str
    final_url: str
    status_code: int = 0
    content_type: str = ""
    response_time_ms: int = 0
    depth: int = 0
    discovered_from: str | None = None

    # Head / meta
    title: str | None = None
    title_length: int = 0
    meta_description: str | None = None
    meta_description_length: int = 0
    meta_robots: str | None = None
    x_robots_tag: str | None = None
    canonical: str | None = None
    indexability: Indexability = Indexability.INDEXABLE
    indexability_reason: str | None = None

    # Content
    h1: list[str] = []
    h2: list[str] = []
    word_count: int = 0
    lang: str | None = None
    hreflang: list[HreflangEntry] = []
    structured_data_types: list[str] = []

    # Links & images
    internal_links_count: int = 0
    external_links_count: int = 0
    outlinks: list[LinkInfo] = []
    broken_links: list[LinkInfo] = []
    images_count: int = 0
    images_missing_alt: int = 0

    # Redirects
    redirect_chain: list[RedirectHop] = []

    # Findings & score
    issues: list[Issue] = []
    score: int = 100


class CrawlSummary(AppModel):
    total_pages: int = 0
    by_status_class: dict[str, int] = {}  # "2xx","3xx","4xx","5xx"
    by_severity: dict[str, int] = {}
    indexable_pages: int = 0
    non_indexable_pages: int = 0
    pages_with_issues: int = 0
    avg_score: float = 0.0
    broken_links_total: int = 0
    missing_titles: int = 0
    duplicate_titles: int = 0
    missing_meta_descriptions: int = 0


class CrawlResult(AppModel):
    crawl_id: str
    start_url: str
    config: CrawlConfig
    started_at: datetime
    finished_at: datetime | None = None
    pages: list[PageAuditResult] = []
    summary: CrawlSummary = CrawlSummary()
    top_issues: list[Issue] = []


class SitemapUrl(AppModel):
    loc: str
    lastmod: str | None = None
    changefreq: str | None = None
    priority: float | None = None


class CrawlComparison(AppModel):
    """Diff between two crawls of the same site (Screaming Frog compare-crawls)."""

    base_crawl_id: str
    new_crawl_id: str
    added_urls: list[str] = []
    removed_urls: list[str] = []
    status_changes: list[dict[str, object]] = []
    score_changes: list[dict[str, object]] = []
    new_issues: int = 0
    resolved_issues: int = 0
