"""Deterministic on-page analysis and rule-based issue detection for crawled pages.

``analyze_page`` turns a raw :class:`~app.core.crawler.fetcher.FetchResponse` into a
fully populated :class:`~app.models.audit.PageAuditResult` by parsing the HTML and
running a fixed rule set (``run_checks``) that always produces the same issues for
the same input — no randomness, no network, no wall-clock-sensitive behaviour.
"""
from __future__ import annotations

from app.core.crawler.fetcher import FetchResponse
from app.models.audit import CrawlConfig, HreflangEntry, LinkInfo, PageAuditResult
from app.models.common import Indexability, Issue, IssueCategory, Severity
from app.utils.html import parse_html
from app.utils.url import is_internal

# ---- Thresholds (kept as module constants so they are easy to tune/reuse) ----
TITLE_MAX_LENGTH = 60
TITLE_MIN_LENGTH = 30
META_DESCRIPTION_MAX_LENGTH = 160
META_DESCRIPTION_MIN_LENGTH = 70
THIN_CONTENT_WORD_COUNT = 300

# Points subtracted from a starting score of 100 for each issue, keyed by severity.
_SEVERITY_PENALTY: dict[Severity, int] = {
    Severity.CRITICAL: 25,
    Severity.HIGH: 15,
    Severity.MEDIUM: 8,
    Severity.LOW: 3,
    Severity.INFO: 0,
}


def _get_header(headers: dict[str, str], name: str) -> str | None:
    """Case-insensitive header lookup (fetcher backends may not normalize casing)."""
    target = name.lower()
    for key, value in headers.items():
        if key.lower() == target:
            return value
    return None


def _classify_indexability(
    status_code: int, meta_robots: str | None, x_robots_tag: str | None
) -> tuple[Indexability, str | None]:
    if not (200 <= status_code < 300):
        return Indexability.NON_INDEXABLE, f"non-2xx status ({status_code})"
    if _has_noindex(meta_robots, x_robots_tag):
        return Indexability.NON_INDEXABLE, "noindex directive"
    return Indexability.INDEXABLE, None


def _has_noindex(meta_robots: str | None, x_robots_tag: str | None) -> bool:
    combined = f"{meta_robots or ''} {x_robots_tag or ''}".lower()
    return "noindex" in combined


def analyze_page(url: str, resp: FetchResponse, root_url: str, config: CrawlConfig) -> PageAuditResult:
    """Parse a fetched response and produce a fully-populated :class:`PageAuditResult`.

    ``root_url`` is the crawl's start URL and is used purely to classify each
    outlink as internal/external (via :func:`app.utils.url.is_internal`).
    ``config`` is accepted for forward-compatibility (e.g. custom thresholds)
    even though the default rule set does not need any of its fields today.
    """
    final_url = resp.final_url or url
    parsed = parse_html(resp.text, base_url=final_url)

    title = parsed.title or None
    meta_description = parsed.meta_description or None
    x_robots_tag = _get_header(resp.headers, "x-robots-tag")

    hreflang = [HreflangEntry(lang=lang, href=href) for lang, href in parsed.hreflang]

    outlinks: list[LinkInfo] = []
    internal_count = 0
    external_count = 0
    for link in parsed.links:
        internal = is_internal(link.href, root_url)
        if internal:
            internal_count += 1
        else:
            external_count += 1
        outlinks.append(
            LinkInfo(
                source_url=final_url,
                target_url=link.href,
                anchor_text=link.anchor,
                rel=link.rel,
                is_internal=internal,
                status_code=None,
            )
        )

    images_count = len(parsed.images)
    images_missing_alt = sum(1 for img in parsed.images if not img.alt)

    indexability, indexability_reason = _classify_indexability(
        resp.status_code, parsed.meta_robots, x_robots_tag
    )

    page = PageAuditResult(
        url=url,
        final_url=final_url,
        status_code=resp.status_code,
        content_type=resp.content_type,
        response_time_ms=resp.elapsed_ms,
        title=title,
        title_length=len(title) if title else 0,
        meta_description=meta_description,
        meta_description_length=len(meta_description) if meta_description else 0,
        meta_robots=parsed.meta_robots,
        x_robots_tag=x_robots_tag,
        canonical=parsed.canonical,
        indexability=indexability,
        indexability_reason=indexability_reason,
        h1=list(parsed.h1),
        h2=list(parsed.h2),
        word_count=parsed.word_count,
        lang=parsed.lang,
        hreflang=hreflang,
        structured_data_types=list(parsed.json_ld_types),
        internal_links_count=internal_count,
        external_links_count=external_count,
        outlinks=outlinks,
        images_count=images_count,
        images_missing_alt=images_missing_alt,
        redirect_chain=list(resp.redirect_chain),
    )

    page.issues = run_checks(page)
    page.score = score_page(page.issues)
    return page


def _issue(
    code: str,
    title: str,
    description: str,
    category: IssueCategory,
    severity: Severity,
    recommendation: str,
) -> Issue:
    return Issue(
        code=code,
        title=title,
        description=description,
        category=category,
        severity=severity,
        recommendation=recommendation,
    )


def run_checks(page: PageAuditResult) -> list[Issue]:
    """Deterministic rule-based checks applied to a single analyzed page.

    Pure function of ``page`` — always returns the same issues for the same
    input, so it is safe to call again (e.g. after the crawl engine discovers a
    broken outlink and updates ``page.broken_links``) to recompute findings.
    """
    issues: list[Issue] = []

    if not page.title:
        issues.append(
            _issue(
                "missing_title",
                "Missing title tag",
                "The page has no <title> element.",
                IssueCategory.ON_PAGE,
                Severity.HIGH,
                "Add a unique, descriptive <title> tag between 30 and 60 characters.",
            )
        )
    elif page.title_length > TITLE_MAX_LENGTH:
        issues.append(
            _issue(
                "title_too_long",
                "Title tag too long",
                f"Title is {page.title_length} characters (recommended max {TITLE_MAX_LENGTH}).",
                IssueCategory.ON_PAGE,
                Severity.MEDIUM,
                "Shorten the title so it is not truncated in search results.",
            )
        )
    elif page.title_length < TITLE_MIN_LENGTH:
        issues.append(
            _issue(
                "title_too_short",
                "Title tag too short",
                f"Title is {page.title_length} characters (recommended min {TITLE_MIN_LENGTH}).",
                IssueCategory.ON_PAGE,
                Severity.MEDIUM,
                "Expand the title to better describe the page's content.",
            )
        )

    if not page.meta_description:
        issues.append(
            _issue(
                "missing_meta_description",
                "Missing meta description",
                "The page has no meta description tag.",
                IssueCategory.ON_PAGE,
                Severity.MEDIUM,
                "Add a unique meta description between 70 and 160 characters.",
            )
        )
    elif page.meta_description_length > META_DESCRIPTION_MAX_LENGTH:
        issues.append(
            _issue(
                "meta_description_too_long",
                "Meta description too long",
                f"Meta description is {page.meta_description_length} characters "
                f"(recommended max {META_DESCRIPTION_MAX_LENGTH}).",
                IssueCategory.ON_PAGE,
                Severity.LOW,
                "Shorten the meta description so it is not truncated in search results.",
            )
        )
    elif page.meta_description_length < META_DESCRIPTION_MIN_LENGTH:
        issues.append(
            _issue(
                "meta_description_too_short",
                "Meta description too short",
                f"Meta description is {page.meta_description_length} characters "
                f"(recommended min {META_DESCRIPTION_MIN_LENGTH}).",
                IssueCategory.ON_PAGE,
                Severity.LOW,
                "Expand the meta description to better summarize the page.",
            )
        )

    if not page.h1:
        issues.append(
            _issue(
                "missing_h1",
                "Missing H1 heading",
                "The page has no <h1> element.",
                IssueCategory.ON_PAGE,
                Severity.HIGH,
                "Add a single, descriptive <h1> that matches the page's primary topic.",
            )
        )
    elif len(page.h1) > 1:
        issues.append(
            _issue(
                "multiple_h1",
                "Multiple H1 headings",
                f"The page has {len(page.h1)} <h1> elements.",
                IssueCategory.ON_PAGE,
                Severity.MEDIUM,
                "Use a single <h1> per page and demote the others to <h2>/<h3>.",
            )
        )

    if page.word_count < THIN_CONTENT_WORD_COUNT:
        issues.append(
            _issue(
                "thin_content",
                "Thin content",
                f"The page has only {page.word_count} words (recommended min {THIN_CONTENT_WORD_COUNT}).",
                IssueCategory.CONTENT,
                Severity.MEDIUM,
                "Expand the content to provide more comprehensive value for this topic.",
            )
        )

    if _has_noindex(page.meta_robots, page.x_robots_tag):
        issues.append(
            _issue(
                "noindex",
                "Page is set to noindex",
                "The page's meta robots / X-Robots-Tag directives include 'noindex'.",
                IssueCategory.INDEXABILITY,
                Severity.HIGH,
                "Remove the noindex directive if this page should appear in search results.",
            )
        )

    if page.status_code >= 400:
        issues.append(
            _issue(
                "http_error",
                "Page returns an HTTP error",
                f"The page responded with status code {page.status_code}.",
                IssueCategory.TECHNICAL,
                Severity.CRITICAL,
                "Fix the underlying error, or remove/redirect links pointing to this URL.",
            )
        )

    if len(page.redirect_chain) > 1:
        issues.append(
            _issue(
                "redirect_chain_too_long",
                "Redirect chain detected",
                f"The page went through {len(page.redirect_chain)} redirect hops before resolving.",
                IssueCategory.TECHNICAL,
                Severity.LOW,
                "Point links directly at the final destination URL to avoid chained redirects.",
            )
        )

    if page.images_missing_alt > 0:
        issues.append(
            _issue(
                "images_missing_alt",
                "Images missing alt text",
                f"{page.images_missing_alt} image(s) are missing descriptive alt text.",
                IssueCategory.IMAGES,
                Severity.LOW,
                "Add descriptive alt attributes to all meaningful images.",
            )
        )

    if not page.canonical:
        issues.append(
            _issue(
                "missing_canonical",
                "Missing canonical tag",
                "The page has no rel=canonical link element.",
                IssueCategory.TECHNICAL,
                Severity.LOW,
                "Add a self-referencing (or otherwise appropriate) canonical tag.",
            )
        )

    if page.final_url and not page.final_url.lower().startswith("https://"):
        issues.append(
            _issue(
                "non_https_url",
                "Page is not served over HTTPS",
                "The final URL uses an insecure (non-HTTPS) scheme.",
                IssueCategory.SECURITY,
                Severity.MEDIUM,
                "Serve the page over HTTPS and redirect HTTP traffic to it.",
            )
        )

    if page.broken_links:
        issues.append(
            _issue(
                "broken_links_present",
                "Broken internal links detected",
                f"{len(page.broken_links)} internal link(s) on this page point to broken pages.",
                IssueCategory.LINKS,
                Severity.HIGH,
                "Update or remove links pointing to broken (4xx/5xx) pages.",
            )
        )

    return issues


def score_page(issues: list[Issue]) -> int:
    """Start at 100 and subtract a weighted penalty per issue severity; clamp to [0, 100]."""
    score = 100
    for issue in issues:
        score -= _SEVERITY_PENALTY.get(issue.severity, 0)
    return max(0, min(100, score))
