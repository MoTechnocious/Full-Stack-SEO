"""Tests for the crawl/audit engine (app.core.crawler).

Everything here is deterministic and network-free: HTTP responses are simulated
with :class:`StaticFetcher`, never with a real socket, so the suite is fast and
reproducible in CI.
"""
from __future__ import annotations

from app.core.crawler.analyzers import run_checks, score_page
from app.core.crawler.compare import compare_crawls
from app.core.crawler.engine import Crawler, audit_single
from app.core.crawler.fetcher import StaticFetcher
from app.core.crawler.sitemap import generate_sitemap, parse_sitemap
from app.models.audit import CrawlConfig, CrawlResult, PageAuditResult, SitemapUrl
from app.models.common import Issue

HOME_HTML = """
<html>
<head>
  <title>Example Site</title>
  <meta name="description" content="A short example site used for crawler tests and nothing else really." />
</head>
<body>
  <h1>Welcome</h1>
  <p>Just a small home page with enough words to pad things out a little bit more than usual for testing.</p>
  <a href="/about">About us</a>
  <a href="/broken">Broken link</a>
  <a href="https://ext.example/">External site</a>
  <a href="/about">About us again</a>
</body>
</html>
"""

ABOUT_HTML = """
<html>
<head><title>Example Site</title></head>
<body>
  <h1>About</h1>
  <p>About page content that talks about the team and the company mission a little bit for testing.</p>
</body>
</html>
"""


def _fake_site_pages() -> dict[str, dict]:
    """A tiny fake site: home links to /about (twice, for dedupe), /broken (404,
    intentionally omitted so it falls back to StaticFetcher's default 404), and an
    external URL that should never be followed with default crawl settings.
    """
    return {
        "https://site.test/": {"status": 200, "html": HOME_HTML},
        "https://site.test/about": {"status": 200, "html": ABOUT_HTML},
    }


# ---- StaticFetcher ----------------------------------------------------------


async def test_static_fetcher_missing_url_defaults_to_404():
    fetcher = StaticFetcher({"https://site.test/": {"status": 200, "html": "<html><title>Hi</title></html>"}})

    ok = await fetcher.fetch("https://site.test/")
    assert ok.status_code == 200
    assert "Hi" in ok.text

    missing = await fetcher.fetch("https://site.test/does-not-exist")
    assert missing.status_code == 404
    assert missing.text == ""


# ---- Crawler.crawl() ---------------------------------------------------------


async def test_crawl_visits_internal_pages_and_marks_broken_link():
    fetcher = StaticFetcher(_fake_site_pages())
    config = CrawlConfig(start_url="https://site.test/", max_pages=10, max_depth=5)
    result = await Crawler(fetcher, config).crawl()

    visited_urls = {p.url for p in result.pages}
    assert visited_urls == {
        "https://site.test/",
        "https://site.test/about",
        "https://site.test/broken",
    }
    assert "https://ext.example/" not in visited_urls  # external link not followed

    home = next(p for p in result.pages if p.url == "https://site.test/")
    assert home.internal_links_count == 3  # /about, /broken, /about (dup)
    assert home.external_links_count == 1  # ext.example

    broken_targets = {link.target_url for link in home.broken_links}
    assert broken_targets == {"https://site.test/broken"}
    assert home.broken_links[0].status_code == 404


async def test_crawl_respects_max_pages():
    fetcher = StaticFetcher(_fake_site_pages())
    config = CrawlConfig(start_url="https://site.test/", max_pages=2, max_depth=5)
    result = await Crawler(fetcher, config).crawl()

    assert len(result.pages) == 2
    assert "https://site.test/broken" not in {p.url for p in result.pages}


async def test_crawl_summary_counts_and_duplicate_titles():
    fetcher = StaticFetcher(_fake_site_pages())
    config = CrawlConfig(start_url="https://site.test/", max_pages=10, max_depth=5)
    result = await Crawler(fetcher, config).crawl()
    summary = result.summary

    assert summary.total_pages == 3
    assert summary.by_status_class == {"2xx": 2, "4xx": 1}
    assert summary.indexable_pages == 2
    assert summary.non_indexable_pages == 1  # the 404 page
    assert summary.broken_links_total == 1
    assert summary.missing_titles == 1  # only the 404 page has no <title>
    assert summary.duplicate_titles == 1  # home + about share "Example Site"
    assert summary.missing_meta_descriptions == 2  # about + broken
    assert summary.pages_with_issues == 3
    assert result.crawl_id  # non-empty uuid hex
    assert result.finished_at is not None and result.finished_at >= result.started_at


# ---- audit_single() -----------------------------------------------------------


async def test_audit_single_missing_meta_description_flags_issue_and_lowers_score():
    html = (
        "<html><head><title>A Complete Guide To Testing Python Crawlers</title></head>"
        "<body><h1>Guide</h1><p>" + ("word " * 320) + "</p></body></html>"
    )
    fetcher = StaticFetcher({"https://solo.test/": {"status": 200, "html": html}})
    config = CrawlConfig(start_url="https://solo.test/")

    page = await audit_single("https://solo.test/", fetcher, config)

    assert page.meta_description is None
    codes = {issue.code for issue in page.issues}
    assert "missing_meta_description" in codes
    assert page.score < 100


# ---- sitemap.py ----------------------------------------------------------------


def test_generate_and_parse_sitemap_roundtrip():
    entries = [
        SitemapUrl(loc="https://site.test/", lastmod="2026-01-01", changefreq="daily", priority=1.0),
        SitemapUrl(loc="https://site.test/about", changefreq="weekly", priority=0.5),
    ]

    xml = generate_sitemap(entries)
    assert "<urlset" in xml
    assert "http://www.sitemaps.org/schemas/sitemap/0.9" in xml

    parsed = parse_sitemap(xml)
    assert len(parsed) == 2
    assert parsed[0].loc == "https://site.test/"
    assert parsed[0].lastmod == "2026-01-01"
    assert parsed[0].changefreq == "daily"
    assert parsed[0].priority == 1.0
    assert parsed[1].loc == "https://site.test/about"
    assert parsed[1].priority == 0.5

    # Plain strings are also accepted as input.
    xml_plain = generate_sitemap(["https://site.test/only"])
    parsed_plain = parse_sitemap(xml_plain)
    assert parsed_plain == [SitemapUrl(loc="https://site.test/only")]


# ---- compare.py ------------------------------------------------------------------


def _crawl_result(crawl_id: str, pages: list[PageAuditResult]) -> CrawlResult:
    from datetime import datetime, timezone

    return CrawlResult(
        crawl_id=crawl_id,
        start_url="https://site.test/",
        config=CrawlConfig(start_url="https://site.test/"),
        started_at=datetime.now(timezone.utc),
        pages=pages,
    )


def test_compare_crawls_detects_added_url_and_status_change():
    base = _crawl_result(
        "base1",
        [
            PageAuditResult(url="https://site.test/", final_url="https://site.test/", status_code=200, score=90),
            PageAuditResult(
                url="https://site.test/about",
                final_url="https://site.test/about",
                status_code=200,
                score=85,
                issues=[Issue(code="thin_content", title="Thin content")],
            ),
        ],
    )
    new = _crawl_result(
        "new1",
        [
            PageAuditResult(url="https://site.test/", final_url="https://site.test/", status_code=200, score=90),
            PageAuditResult(
                url="https://site.test/about",
                final_url="https://site.test/about",
                status_code=404,
                score=40,
                issues=[
                    Issue(code="http_error", title="HTTP error"),
                    Issue(code="missing_title", title="Missing title"),
                ],
            ),
            PageAuditResult(
                url="https://site.test/new-page",
                final_url="https://site.test/new-page",
                status_code=200,
                score=95,
            ),
        ],
    )

    comparison = compare_crawls(base, new)

    assert comparison.added_urls == ["https://site.test/new-page"]
    assert comparison.removed_urls == []
    assert {"url": "https://site.test/about", "old": 200, "new": 404} in comparison.status_changes
    assert len(comparison.score_changes) == 1
    assert comparison.new_issues == 2  # http_error, missing_title
    assert comparison.resolved_issues == 1  # thin_content no longer present


# ---- analyzers.run_checks / score_page (direct, no HTTP involved) ----------------


def test_run_checks_and_score_page_are_deterministic():
    page = PageAuditResult(
        url="https://site.test/thin",
        final_url="https://site.test/thin",
        status_code=200,
        title=None,
        meta_description=None,
        h1=[],
        word_count=10,
        canonical=None,
    )

    issues = run_checks(page)
    codes = {issue.code for issue in issues}
    assert codes == {
        "missing_title",
        "missing_meta_description",
        "missing_h1",
        "thin_content",
        "missing_canonical",
    }

    score = score_page(issues)
    assert score == 51  # 100 - (15 + 8 + 15 + 8 + 3) for HIGH/MEDIUM/HIGH/MEDIUM/LOW

    # Pure function: re-running on the same page yields identical issues.
    assert run_checks(page) == issues
