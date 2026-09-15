"""Diff two crawl results of (nominally) the same site (Screaming Frog "compare crawls")."""
from __future__ import annotations

from app.models.audit import CrawlComparison, CrawlResult, PageAuditResult


def compare_crawls(base: CrawlResult, new: CrawlResult) -> CrawlComparison:
    """Compute the diff between a ``base`` crawl and a ``new`` (later) crawl.

    Pages are matched by their (pre-redirect) ``url``. Added/removed URLs are the
    set difference; for URLs present in both crawls we diff status code, score,
    and issue codes (new issues introduced vs. issues resolved since the base crawl).
    """
    base_by_url: dict[str, PageAuditResult] = {p.url: p for p in base.pages}
    new_by_url: dict[str, PageAuditResult] = {p.url: p for p in new.pages}

    base_urls = set(base_by_url)
    new_urls = set(new_by_url)

    added_urls = sorted(new_urls - base_urls)
    removed_urls = sorted(base_urls - new_urls)
    common_urls = sorted(base_urls & new_urls)

    status_changes: list[dict[str, object]] = []
    score_changes: list[dict[str, object]] = []
    new_issues = 0
    resolved_issues = 0

    for url in common_urls:
        base_page = base_by_url[url]
        new_page = new_by_url[url]

        if base_page.status_code != new_page.status_code:
            status_changes.append({"url": url, "old": base_page.status_code, "new": new_page.status_code})

        if base_page.score != new_page.score:
            score_changes.append({"url": url, "old": base_page.score, "new": new_page.score})

        base_codes = {issue.code for issue in base_page.issues}
        new_codes = {issue.code for issue in new_page.issues}
        new_issues += len(new_codes - base_codes)
        resolved_issues += len(base_codes - new_codes)

    return CrawlComparison(
        base_crawl_id=base.crawl_id,
        new_crawl_id=new.crawl_id,
        added_urls=added_urls,
        removed_urls=removed_urls,
        status_changes=status_changes,
        score_changes=score_changes,
        new_issues=new_issues,
        resolved_issues=resolved_issues,
    )
