"""Tests for the Local SEO suite (GBP + citations) and the public lead-gen widget.

Fully offline: GBP calls and directory pushes go through deterministic in-memory
mocks, and widget leads flow through the mock CRM adapter — never real HTTP.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.local.citations import (
    CitationSyncEngine,
    MockDirectoryAdapter,
    build_mock_adapters,
    diff_listing,
    reset_citation_engine,
)
from app.core.local.gbp import (
    GbpManager,
    MockGbpProvider,
    classify_review_sentiment,
    reset_gbp_provider,
    suggest_review_reply,
)
from app.db.session import get_session
from app.middleware.errors import register_exception_handlers
from app.models.local import (
    Directory,
    DirectoryListing,
    GbpPostCreate,
    GbpReview,
    ListingDeliveryState,
    NapRecord,
    ReviewSentiment,
)


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Isolate every test from process-wide provider/engine singletons."""
    reset_gbp_provider()
    reset_citation_engine()
    yield
    reset_gbp_provider()
    reset_citation_engine()


def _nap(**overrides) -> NapRecord:
    base = dict(
        name="Acme Dental",
        address="1 Main St, Springfield",
        phone="+15550001111",
        website="https://acmedental.test",
        hours={"mon": "9-5", "tue": "9-5"},
        locked=False,
    )
    base.update(overrides)
    return NapRecord(**base)


# ---------------------------------------------------------------------------
# GBP manager
# ---------------------------------------------------------------------------


class TestMockGbpProvider:
    def test_publish_post_is_org_scoped_with_sequential_ids(self) -> None:
        provider = MockGbpProvider()
        post = provider.publish_post("org-a", GbpPostCreate(summary="Grand opening!"))
        assert post.id == "gbp_000001" and post.org_id == "org-a" and post.state == "live"
        provider.publish_post("org-a", GbpPostCreate(summary="Second post"))
        assert len(provider.list_posts("org-a")) == 2
        assert provider.list_posts("org-b") == []

    def test_metrics_are_deterministic_per_org(self) -> None:
        provider = MockGbpProvider()
        a1 = provider.fetch_metrics("org-a", 30)
        a2 = provider.fetch_metrics("org-a", 30)
        b = provider.fetch_metrics("org-b", 30)
        assert a1 == a2
        assert a1 != b
        assert a1.views_search > 0 and a1.actions_calls > 0

    def test_seeded_reviews_and_reply(self) -> None:
        provider = MockGbpProvider()
        reviews = provider.list_reviews("org-a")
        assert len(reviews) == 3
        # Newest first (rev_003 has the latest fixed created_at).
        assert reviews[0].id == "rev_003"
        replied = provider.reply_to_review("org-a", "rev_001", "Thanks!")
        assert replied is not None and replied.reply == "Thanks!"
        assert provider.reply_to_review("org-a", "rev_999", "x") is None


class TestSuggestedReplies:
    def _review(self, rating: int, text: str, author: str = "Alice M.") -> GbpReview:
        return GbpReview(
            id="rev_x", author=author, rating=rating, text=text,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

    def test_sentiment_classification_by_rating_and_text(self) -> None:
        assert classify_review_sentiment(self._review(5, "Great!")) == ReviewSentiment.POSITIVE
        assert classify_review_sentiment(self._review(1, "Awful")) == ReviewSentiment.NEGATIVE
        assert classify_review_sentiment(self._review(3, "It was okay.")) == ReviewSentiment.NEUTRAL
        # A middling rating with negative-signal words is treated as negative.
        assert (
            classify_review_sentiment(self._review(3, "The wait was terrible."))
            == ReviewSentiment.NEGATIVE
        )

    def test_reply_templates_match_sentiment_and_mention_reviewer(self) -> None:
        positive = suggest_review_reply(self._review(5, "Loved it!"), "Acme Dental")
        assert positive.sentiment == ReviewSentiment.POSITIVE
        assert "Alice" in positive.text and "Acme Dental" in positive.text

        negative = suggest_review_reply(self._review(1, "Bad service", author="Bob K."))
        assert negative.sentiment == ReviewSentiment.NEGATIVE
        assert "sorry" in negative.text.lower() and "Bob" in negative.text

        neutral = suggest_review_reply(self._review(3, "It was fine."))
        assert neutral.sentiment == ReviewSentiment.NEUTRAL
        assert "feedback" in neutral.text.lower()

    def test_manager_reply_falls_back_to_suggestion(self) -> None:
        provider = MockGbpProvider()
        manager = GbpManager(provider)
        review = manager.reply("org-a", "rev_003", text=None)  # rev_003 is the 1-star seed
        assert review is not None and review.reply
        assert "sorry" in review.reply.lower()
        # Replied reviews drop out of the suggestions list.
        pending = {s.review_id for s in manager.suggested_replies("org-a")}
        assert "rev_003" not in pending and "rev_001" in pending


# ---------------------------------------------------------------------------
# Citation distributor
# ---------------------------------------------------------------------------


class _FailingAdapter:
    """Always raises on push. Exercises per-directory failure reporting."""

    provider = "failing"

    def __init__(self, directory: Directory = Directory.YELP) -> None:
        self.directory = directory

    def fetch(self, org_id: str) -> DirectoryListing | None:
        return None

    def push(self, org_id: str, nap: NapRecord) -> DirectoryListing:
        raise RuntimeError("simulated directory push failure")


class TestCitationSync:
    def test_first_sync_creates_all_listings_then_in_sync(self) -> None:
        engine = CitationSyncEngine(build_mock_adapters())
        engine.set_nap("org-a", _nap())

        report = engine.sync("org-a")
        assert {r.directory for r in report.results} == set(Directory)
        assert all(r.state == ListingDeliveryState.CREATED for r in report.results)
        assert report.delivered == 4 and report.failed == 0

        again = engine.sync("org-a")
        assert all(r.state == ListingDeliveryState.IN_SYNC for r in again.results)

    def test_sync_corrects_drift_with_field_level_diffs(self) -> None:
        adapters = build_mock_adapters()
        engine = CitationSyncEngine(adapters)
        engine.set_nap("org-a", _nap())
        engine.sync("org-a")

        # Simulate drift on Yelp: someone changed the phone number.
        drifted = adapters[0].fetch("org-a")
        assert drifted is not None
        drifted.phone = "+19999999999"
        adapters[0].seed("org-a", drifted)

        report = engine.sync("org-a")
        by_dir = {r.directory: r for r in report.results}
        yelp = by_dir[Directory.YELP]
        assert yelp.state == ListingDeliveryState.UPDATED
        assert [d.field for d in yelp.diffs] == ["phone"]
        assert yelp.diffs[0].expected == "+15550001111"
        assert yelp.diffs[0].found == "+19999999999"
        # Drift is corrected by the push.
        assert adapters[0].fetch("org-a").phone == "+15550001111"

    def test_failed_adapter_reported_not_raised(self) -> None:
        engine = CitationSyncEngine(
            [_FailingAdapter(Directory.YELP), MockDirectoryAdapter(Directory.FOURSQUARE)]
        )
        engine.set_nap("org-a", _nap())
        report = engine.sync("org-a")
        by_dir = {r.directory: r for r in report.results}
        assert by_dir[Directory.YELP].state == ListingDeliveryState.FAILED
        assert "simulated directory push failure" in (by_dir[Directory.YELP].error or "")
        assert by_dir[Directory.FOURSQUARE].state == ListingDeliveryState.CREATED
        assert report.delivered == 1 and report.failed == 1

    def test_sync_without_nap_raises_key_error(self) -> None:
        engine = CitationSyncEngine(build_mock_adapters())
        with pytest.raises(KeyError):
            engine.sync("org-a")
        with pytest.raises(KeyError):
            engine.status("org-a")

    def test_status_flags_drift_when_unlocked(self) -> None:
        adapters = build_mock_adapters()
        engine = CitationSyncEngine(adapters)
        engine.set_nap("org-a", _nap(locked=False))
        engine.sync("org-a")

        drifted = adapters[1].fetch("org-a")
        drifted.name = "Acme Dental LLC"
        adapters[1].seed("org-a", drifted)

        status = engine.status("org-a")
        assert status.drift_detected is True and status.locked is False
        by_dir = {s.directory: s for s in status.directories}
        assert by_dir[adapters[1].directory].state == ListingDeliveryState.DRIFT_FLAGGED
        assert by_dir[adapters[1].directory].drift is True
        # Unlocked -> the drifted value is flagged but NOT overwritten.
        assert adapters[1].fetch("org-a").name == "Acme Dental LLC"

    def test_status_blocks_drift_when_locked(self) -> None:
        adapters = build_mock_adapters()
        engine = CitationSyncEngine(adapters)
        engine.set_nap("org-a", _nap(locked=True))
        engine.sync("org-a")

        drifted = adapters[2].fetch("org-a")
        drifted.address = "999 Wrong Ave"
        adapters[2].seed("org-a", drifted)

        status = engine.status("org-a")
        by_dir = {s.directory: s for s in status.directories}
        assert by_dir[adapters[2].directory].state == ListingDeliveryState.DRIFT_BLOCKED
        # Locked -> the canonical NAP was re-pushed over the drift.
        assert adapters[2].fetch("org-a").address == "1 Main St, Springfield"
        # A follow-up status shows everything back in sync.
        assert engine.status("org-a").drift_detected is False

    def test_hours_diff_detected(self) -> None:
        listing = DirectoryListing(
            directory=Directory.YELP, name="Acme Dental",
            address="1 Main St, Springfield", phone="+15550001111",
            website="https://acmedental.test", hours={"mon": "10-4"},
        )
        diffs = diff_listing(_nap(), listing)
        assert [d.field for d in diffs] == ["hours"]


# ---------------------------------------------------------------------------
# API routes (local + widget routers mounted on a minimal app, spine-style)
# ---------------------------------------------------------------------------


def _local_app(test_engine) -> FastAPI:
    from app.api.routes_local import router as local_router
    from app.api.routes_widget import router as widget_router

    app = FastAPI()

    def _get_session():
        with Session(test_engine) as s:
            yield s

    app.dependency_overrides[get_session] = _get_session
    register_exception_handlers(app)
    app.include_router(local_router)
    app.include_router(widget_router)
    return app


class TestLocalApi:
    def test_requires_authentication(self, test_engine) -> None:
        client = TestClient(_local_app(test_engine))
        assert client.get("/local/gbp/reviews").status_code == 401
        assert client.get("/local/citations/nap").status_code == 401

    def test_gbp_posts_metrics_reviews_and_reply(self, test_engine, make_auth) -> None:
        info = make_auth()
        client = TestClient(_local_app(test_engine))
        headers = info["headers"]

        r = client.post(
            "/local/gbp/posts", headers=headers,
            json={"summary": "Summer special!", "topic": "offer"},
        )
        assert r.status_code == 200
        assert r.json()["summary"] == "Summer special!" and r.json()["org_id"] == info["org_id"]

        m1 = client.get("/local/gbp/metrics", headers=headers, params={"period_days": 30})
        m2 = client.get("/local/gbp/metrics", headers=headers, params={"period_days": 30})
        assert m1.status_code == 200 and m1.json() == m2.json()

        r = client.get("/local/gbp/reviews", headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert len(body["reviews"]) == 3
        assert len(body["suggested_replies"]) == 3
        review_id = body["reviews"][0]["id"]

        r = client.post(
            f"/local/gbp/reviews/{review_id}/reply", headers=headers, json={"text": None}
        )
        assert r.status_code == 200 and r.json()["reply"]

        assert (
            client.post("/local/gbp/reviews/rev_999/reply", headers=headers, json={}).status_code
            == 404
        )

    def test_citations_nap_roundtrip_sync_and_status(self, test_engine, make_auth) -> None:
        info = make_auth()
        client = TestClient(_local_app(test_engine))
        headers = info["headers"]

        # Nothing configured yet.
        assert client.get("/local/citations/nap", headers=headers).status_code == 404
        assert client.post("/local/citations/sync", headers=headers).status_code == 404
        assert client.get("/local/citations/status", headers=headers).status_code == 404

        nap = _nap().model_dump()
        r = client.put("/local/citations/nap", headers=headers, json=nap)
        assert r.status_code == 200 and r.json()["name"] == "Acme Dental"
        assert client.get("/local/citations/nap", headers=headers).json()["phone"] == "+15550001111"

        r = client.post("/local/citations/sync", headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert body["delivered"] == 4 and body["failed"] == 0
        assert {res["state"] for res in body["results"]} == {"created"}

        r = client.get("/local/citations/status", headers=headers)
        assert r.status_code == 200
        assert r.json()["drift_detected"] is False
        assert all(d["state"] == "in_sync" for d in r.json()["directories"])

    def test_citations_sync_single_directory(self, test_engine, make_auth) -> None:
        info = make_auth()
        client = TestClient(_local_app(test_engine))
        headers = info["headers"]
        client.put("/local/citations/nap", headers=headers, json=_nap().model_dump())
        r = client.post("/local/citations/sync", headers=headers, params={"directory": "yelp"})
        assert r.status_code == 200
        assert [res["directory"] for res in r.json()["results"]] == ["yelp"]


class TestWidgetApi:
    def test_audit_js_is_public_and_branded(self, test_engine) -> None:
        client = TestClient(_local_app(test_engine))
        r = client.get("/widget/audit.js", params={"org": "Acme SEO!"})
        assert r.status_code == 200  # no auth header required
        assert r.headers["content-type"].startswith("application/javascript")
        assert '"acme-seo"' in r.text  # slug sanitized and injected
        assert "/widget/leads" in r.text
        # Default branding when no org given.
        assert '"default"' in client.get("/widget/audit.js").text

    def test_lead_capture_returns_deterministic_teaser(self, test_engine) -> None:
        client = TestClient(_local_app(test_engine))
        payload = {"url": "example.com", "email": "jane@example.com", "org": "acme"}
        r1 = client.post("/widget/leads", json=payload)  # public: no auth header
        assert r1.status_code == 200
        body = r1.json()
        assert body["status"] == "delivered"
        assert body["lead_id"]
        teaser = body["teaser"]
        assert teaser["site"] == "example.com"
        assert 45 <= teaser["score"] <= 85
        assert teaser["grade"]
        assert len(teaser["top_findings"]) == 3

        # Same URL -> identical mock mini-audit.
        r2 = client.post("/widget/leads", json=payload)
        assert r2.json()["teaser"] == teaser
        # Different domain -> (deterministically) different teaser site.
        other = client.post(
            "/widget/leads",
            json={"url": "https://other.example.org/page", "email": "jane@example.com"},
        )
        assert other.json()["teaser"]["site"] == "other.example.org"

    def test_invalid_lead_is_rejected_without_teaser(self, test_engine) -> None:
        client = TestClient(_local_app(test_engine))
        r = client.post(
            "/widget/leads", json={"url": "example.com", "email": "not-an-email", "org": "acme"}
        )
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "rejected"
        assert body["teaser"] is None
        assert any("email" in e.lower() for e in body["errors"])

    def test_name_defaults_from_email_local_part(self, test_engine) -> None:
        client = TestClient(_local_app(test_engine))
        r = client.post(
            "/widget/leads",
            json={"url": "example.com", "email": "grace.hopper@example.com", "name": None},
        )
        assert r.json()["status"] == "delivered"  # name requirement satisfied by fallback
