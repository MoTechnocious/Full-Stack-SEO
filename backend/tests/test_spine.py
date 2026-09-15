"""Smoke tests for the shared spine (models, utils, store) before module builds."""
from __future__ import annotations

from app.models.audit import CrawlConfig, PageAuditResult
from app.models.common import Severity, grade_from_score
from app.services.store import InMemoryStore
from app.utils.html import parse_html
from app.utils.text import extract_terms, flesch_reading_ease, keyword_density, word_count
from app.utils.url import is_internal, normalize_url, registrable_domain


def test_severity_ordering():
    assert Severity.CRITICAL.weight > Severity.LOW.weight
    assert grade_from_score(95) == "A"
    assert grade_from_score(10) == "F"


def test_url_helpers():
    assert normalize_url("/a", "https://Example.com") == "https://example.com/a"
    assert normalize_url("https://example.com:443/x") == "https://example.com/x"
    assert registrable_domain("https://www.bbc.co.uk/news") == "bbc.co.uk"
    assert is_internal("https://blog.example.com", "https://example.com") is True
    assert is_internal("https://other.org", "https://example.com") is False


def test_text_helpers():
    assert word_count("one two three") == 3
    assert keyword_density("seo seo tool", "seo") > 0
    assert 0 <= flesch_reading_ease("This is a simple short sentence.") <= 100
    terms = dict(extract_terms("running shoes running shoes comfort", top_k=5))
    assert any("running" in t for t in terms)


def test_parse_html(sample_html):
    page = parse_html(sample_html, base_url="https://example.com/running-shoes")
    assert page.title and "Running Shoes" in page.title
    assert page.meta_description
    assert page.canonical == "https://example.com/running-shoes"
    assert "Article" in page.json_ld_types
    assert len(page.h1) == 1
    assert any(img.alt for img in page.images)
    assert any(img.alt is None for img in page.images)  # one image missing alt
    assert any(link.href.startswith("https://external") for link in page.links)


def test_store_roundtrip():
    store = InMemoryStore()
    cfg = CrawlConfig(start_url="https://example.com")
    from datetime import datetime, timezone

    from app.models.audit import CrawlResult

    crawl = CrawlResult(
        crawl_id="c1",
        start_url="https://example.com",
        config=cfg,
        started_at=datetime.now(timezone.utc),
        pages=[PageAuditResult(url="https://example.com", final_url="https://example.com")],
    )
    store.save_crawl(crawl)
    assert store.get_crawl("c1") is crawl
    assert len(store.list_crawls()) == 1
