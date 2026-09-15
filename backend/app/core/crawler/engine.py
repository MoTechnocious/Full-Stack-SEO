"""BFS crawl engine: walks a site via a pluggable :class:`Fetcher`, audits every
page it visits, and aggregates the results into a :class:`CrawlResult`.
"""
from __future__ import annotations

import re
import uuid
from collections import Counter, deque
from datetime import datetime, timezone
from typing import Callable

from app.core.crawler.analyzers import analyze_page, run_checks, score_page
from app.core.crawler.fetcher import Fetcher
from app.models.audit import CrawlConfig, CrawlResult, CrawlSummary, PageAuditResult
from app.models.common import Indexability, Issue
from app.utils.url import is_http_url, is_internal, normalize_url


class Crawler:
    """BFS crawler that fetches pages via a pluggable :class:`Fetcher` and audits each one."""

    def __init__(self, fetcher: Fetcher, config: CrawlConfig) -> None:
        self.fetcher = fetcher
        self.config = config

    async def crawl(self) -> CrawlResult:
        config = self.config
        root_url = normalize_url(config.start_url)
        allowed = _pattern_filter(config.include_patterns, config.exclude_patterns)

        visited: set[str] = set()
        pages_by_url: dict[str, PageAuditResult] = {}
        queue: deque[tuple[str, int, str | None]] = deque()

        if allowed(root_url):
            queue.append((root_url, 0, None))
            visited.add(root_url)

        started_at = datetime.now(timezone.utc)

        while queue and len(pages_by_url) < config.max_pages:
            url, depth, discovered_from = queue.popleft()

            resp = await self.fetcher.fetch(url)
            page = analyze_page(url, resp, root_url, config)
            page.depth = depth
            page.discovered_from = discovered_from
            pages_by_url[url] = page

            if depth >= config.max_depth:
                continue

            for link in page.outlinks:
                if not link.is_internal and not config.follow_external:
                    continue
                if not is_http_url(link.target_url):
                    continue
                target = normalize_url(link.target_url)
                if target in visited or not allowed(target):
                    continue
                visited.add(target)
                queue.append((target, depth + 1, url))

        _mark_broken_links(pages_by_url)

        finished_at = datetime.now(timezone.utc)
        pages = list(pages_by_url.values())

        return CrawlResult(
            crawl_id=uuid.uuid4().hex,
            start_url=config.start_url,
            config=config,
            started_at=started_at,
            finished_at=finished_at,
            pages=pages,
            summary=_build_summary(pages),
            top_issues=_top_issues(pages),
        )


async def audit_single(url: str, fetcher: Fetcher, config: CrawlConfig | None = None) -> PageAuditResult:
    """Fetch a single URL and run the full page analysis on it (no crawling/BFS)."""
    cfg = config or CrawlConfig(start_url=url)
    normalized_url = normalize_url(url)
    root_url = normalize_url(cfg.start_url)
    resp = await fetcher.fetch(normalized_url)
    return analyze_page(normalized_url, resp, root_url, cfg)


def _pattern_filter(include_patterns: list[str], exclude_patterns: list[str]) -> Callable[[str], bool]:
    include_re = [re.compile(p) for p in include_patterns]
    exclude_re = [re.compile(p) for p in exclude_patterns]

    def allowed(url: str) -> bool:
        if exclude_re and any(p.search(url) for p in exclude_re):
            return False
        if include_re and not any(p.search(url) for p in include_re):
            return False
        return True

    return allowed


def _mark_broken_links(pages_by_url: dict[str, PageAuditResult]) -> None:
    """After every reachable page has been fetched, flag internal outlinks whose
    target resolved to an HTTP error, then re-run the rule checks so
    ``broken_links_present`` (and the page score) reflect the finding.
    """
    for page in pages_by_url.values():
        changed = False
        for link in page.outlinks:
            if not link.is_internal:
                continue
            target_page = pages_by_url.get(normalize_url(link.target_url))
            if target_page is not None and target_page.status_code >= 400:
                page.broken_links.append(link.model_copy(update={"status_code": target_page.status_code}))
                changed = True
        if changed:
            page.issues = run_checks(page)
            page.score = score_page(page.issues)


def _status_class(status_code: int) -> str:
    if status_code >= 100:
        return f"{status_code // 100}xx"
    return "other"


def _build_summary(pages: list[PageAuditResult]) -> CrawlSummary:
    total = len(pages)
    by_status_class: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    indexable = 0
    non_indexable = 0
    pages_with_issues = 0
    broken_links_total = 0
    missing_titles = 0
    missing_meta_descriptions = 0
    title_counts: Counter[str] = Counter()
    score_sum = 0

    for page in pages:
        cls = _status_class(page.status_code)
        by_status_class[cls] = by_status_class.get(cls, 0) + 1

        if page.indexability == Indexability.INDEXABLE:
            indexable += 1
        else:
            non_indexable += 1

        if page.issues:
            pages_with_issues += 1
        for issue in page.issues:
            by_severity[issue.severity.value] = by_severity.get(issue.severity.value, 0) + 1

        broken_links_total += len(page.broken_links)

        if page.title:
            title_counts[page.title] += 1
        else:
            missing_titles += 1

        if not page.meta_description:
            missing_meta_descriptions += 1

        score_sum += page.score

    duplicate_titles = sum(1 for count in title_counts.values() if count > 1)
    avg_score = round(score_sum / total, 2) if total else 0.0

    return CrawlSummary(
        total_pages=total,
        by_status_class=by_status_class,
        by_severity=by_severity,
        indexable_pages=indexable,
        non_indexable_pages=non_indexable,
        pages_with_issues=pages_with_issues,
        avg_score=avg_score,
        broken_links_total=broken_links_total,
        missing_titles=missing_titles,
        duplicate_titles=duplicate_titles,
        missing_meta_descriptions=missing_meta_descriptions,
    )


def _top_issues(pages: list[PageAuditResult], limit: int = 10) -> list[Issue]:
    """Aggregate issues across all pages, deduped by code, ordered by severity."""
    by_code: dict[str, Issue] = {}
    for page in pages:
        for issue in page.issues:
            by_code.setdefault(issue.code, issue)
    ordered = sorted(by_code.values(), key=lambda issue: issue.severity.weight, reverse=True)
    return ordered[:limit]
