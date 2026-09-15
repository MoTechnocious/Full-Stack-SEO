"""Tenant-aware integration tests for the SEO API surface."""
from __future__ import annotations

import hashlib
import hmac
import json

API = "/api/v1"


def _crawl(client, headers):
    return client.post(
        f"{API}/audit/crawl", json={"start_url": "https://site.test/", "max_pages": 10}, headers=headers
    )


def test_endpoints_require_auth(app_client):
    assert app_client.post(f"{API}/audit/crawl", json={"start_url": "https://site.test/"}).status_code == 401
    assert app_client.post(f"{API}/keywords/research", json={"seed": "x"}).status_code == 401
    assert app_client.get(f"{API}/rankings/site.test").status_code == 401


def test_audit_page_and_crawl_isolation(app_client, make_auth):
    a = make_auth(email="a@x.test", org_name="Org A", plan_code="agency")
    b = make_auth(email="b@x.test", org_name="Org B", plan_code="agency")
    page = app_client.post(
        f"{API}/audit/page",
        json={"html": "<html><head><title>Hi</title></head><body><p>x</p></body></html>", "url": "https://ex.com/p"},
        headers=a["headers"],
    )
    assert page.status_code == 200 and 0 <= page.json()["score"] <= 100
    r = _crawl(app_client, a["headers"])
    assert r.status_code == 200
    cid = r.json()["crawl_id"]
    assert app_client.get(f"{API}/audit/crawl/{cid}", headers=a["headers"]).status_code == 200
    # org B cannot read org A's crawl (tenant isolation)
    assert app_client.get(f"{API}/audit/crawl/{cid}", headers=b["headers"]).status_code == 404


def test_onpage_and_keywords(app_client, make_auth):
    h = make_auth(plan_code="agency")["headers"]
    assert app_client.post(
        f"{API}/onpage/analyze",
        json={"target_keyword": "running shoes",
              "html": "<html><head><title>Running shoes</title></head><body><h1>Running shoes</h1><p>running shoes are great</p></body></html>"},
        headers=h,
    ).status_code == 200
    cs = app_client.post(
        f"{API}/onpage/content-score",
        json={"target_keyword": "shoes", "content": "shoes " * 200, "competitor_texts": ["shoes comfort " * 100]},
        headers=h,
    )
    assert cs.status_code == 200 and 0 <= cs.json()["content_score"] <= 100
    assert app_client.post(f"{API}/onpage/schema", json={"schema_type": "FAQPage", "fields": {}}, headers=h).json()["warnings"]
    kr = app_client.post(f"{API}/keywords/research", json={"seed": "running shoes", "limit": 12}, headers=h)
    assert kr.status_code == 200 and len(kr.json()["keywords"]) == 12
    assert len(app_client.post(f"{API}/keywords/serp", json={"keyword": "x"}, headers=h).json()["results"]) == 10


def test_rankings_and_reports(app_client, make_auth):
    h = make_auth(plan_code="agency")["headers"]
    tr = app_client.post(f"{API}/rankings/track", json={"domain": "site.test", "keywords": ["a", "b", "c"]}, headers=h)
    assert tr.status_code == 200 and tr.json()["total_keywords"] == 3
    assert app_client.get(f"{API}/rankings/site.test", headers=h).status_code == 200
    crawl = _crawl(app_client, h).json()
    plan = app_client.post(f"{API}/reports/action-plan", json={"site": "site.test", "crawl_id": crawl["crawl_id"]}, headers=h)
    assert plan.status_code == 200
    html = app_client.post(
        f"{API}/reports/build?format=html",
        json={"site": "site.test", "period_start": "2026-06-01", "period_end": "2026-06-30",
              "branding": {"agency_name": "Acme SEO"}, "crawl_id": crawl["crawl_id"]},
        headers=h,
    )
    assert html.status_code == 200 and "Acme SEO" in html.text


def test_white_label_gated_on_free_plan(app_client, make_auth):
    h = make_auth(email="free@x.test", org_name="Free Co", plan_code="free")["headers"]
    crawl = _crawl(app_client, h).json()
    html = app_client.post(
        f"{API}/reports/build?format=html",
        json={"site": "site.test", "period_start": "2026-06-01", "period_end": "2026-06-30",
              "branding": {"agency_name": "Should Not Appear"}, "crawl_id": crawl["crawl_id"]},
        headers=h,
    )
    assert html.status_code == 200
    assert "Should Not Appear" not in html.text  # branding ignored without white_label feature


def test_quota_enforced_on_free_plan(app_client, make_auth):
    h = make_auth(email="q@x.test", org_name="Quota Co", plan_code="free")["headers"]
    for _ in range(5):  # free plan allows 5 crawls/month
        assert _crawl(app_client, h).status_code == 200
    assert _crawl(app_client, h).status_code == 402  # 6th exceeds quota


def test_integrations_leads_and_webhook(app_client, make_auth):
    h = make_auth(plan_code="agency")["headers"]
    lead = app_client.post(
        f"{API}/integrations/leads",
        json={"name": "Jane", "email": "jane@example.com", "website": "example.com"}, headers=h,
    )
    assert lead.status_code == 200 and lead.json()["status"] in {"delivered", "sent"}
    assert len(app_client.get(f"{API}/integrations/deliveries", headers=h).json()) >= 1
    secret = "change-me-in-env"
    payload = json.dumps({"type": "ping"}).encode()
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    wh = app_client.post(
        f"{API}/integrations/webhooks/make", content=payload,
        headers={"X-Signature": sig, "Content-Type": "application/json"},
    )
    assert wh.status_code == 200 and wh.json()["verified"] is True


def test_validation_error(app_client, make_auth):
    h = make_auth(plan_code="agency")["headers"]
    r = app_client.post(f"{API}/keywords/research", json={}, headers=h)  # missing 'seed'
    assert r.status_code == 422 and r.json()["error"] == "validation_failed"
