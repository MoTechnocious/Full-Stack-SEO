"""Tests for the Kit assistant: advisor, agentic queue, keyword mapping, calendar.

Fully offline: content generation, CMS updates, GBP posts, and directory syncs
all go through deterministic in-memory mocks — never real HTTP.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.assistant.advisor import build_action_items
from app.core.assistant.calendar import build_content_calendar
from app.core.assistant.execution import (
    ActionExecutor,
    ActionQueueService,
    MockCmsAdapter,
    MockContentGenerator,
    reset_execution_state,
)
from app.core.assistant.mapping import map_keywords
from app.core.local.citations import (
    CitationSyncEngine,
    build_mock_adapters,
    reset_citation_engine,
)
from app.core.local.gbp import MockGbpProvider, reset_gbp_provider
from app.db.session import get_session
from app.middleware.errors import register_exception_handlers
from app.models.assistant import (
    ActionType,
    BlogDraft,
    CalendarCadence,
    ExecutionStatus,
    SitePage,
)
from app.models.audit import CrawlConfig, CrawlResult, PageAuditResult
from app.models.common import Issue, IssueCategory, SearchIntent, Severity
from app.models.keywords import Keyword, RankTrackingSummary, TrackedKeyword
from app.models.local import NapRecord


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Isolate every test from process-wide queue/provider singletons."""
    reset_execution_state()
    reset_gbp_provider()
    reset_citation_engine()
    yield
    reset_execution_state()
    reset_gbp_provider()
    reset_citation_engine()


def _make_audit(site_url: str = "https://example.com") -> CrawlResult:
    page = PageAuditResult(
        url=f"{site_url}/",
        final_url=f"{site_url}/",
        status_code=200,
        score=60,
        issues=[
            Issue(
                code="missing_meta_description",
                title="Missing meta description",
                description="The page has no meta description.",
                category=IssueCategory.ON_PAGE,
                severity=Severity.HIGH,
                recommendation="Add a unique 150-160 character meta description.",
            ),
            Issue(
                code="broken_link",
                title="Broken internal link",
                description="A link on this page returns a 404.",
                category=IssueCategory.LINKS,
                severity=Severity.CRITICAL,
            ),
        ],
    )
    return CrawlResult(
        crawl_id="crawl-1",
        start_url=site_url,
        config=CrawlConfig(start_url=site_url),
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        pages=[page],
    )


def _make_rank_summary(domain: str = "example.com") -> RankTrackingSummary:
    return RankTrackingSummary(
        domain=domain,
        total_keywords=2,
        keywords=[
            TrackedKeyword(
                keyword="best running shoes", domain=domain,
                search_volume=2400, current_position=13, previous_position=15,
            ),
            TrackedKeyword(
                keyword="marathon training plan", domain=domain,
                search_volume=500, current_position=45, previous_position=40,
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Advisor: audit -> guided action items
# ---------------------------------------------------------------------------


class TestAdvisor:
    def test_items_are_plain_english_prioritized_and_guided(self) -> None:
        plan = build_action_items("example.com", audit=_make_audit())

        assert plan.total == 2
        # Critical (broken link) outranks high (meta description).
        assert plan.items[0].source_code == "broken_link"
        scores = [i.priority_score for i in plan.items]
        assert scores == sorted(scores, reverse=True)
        assert sum(plan.by_severity.values()) == plan.total
        for item in plan.items:
            assert item.what_it_means and item.why_it_matters
            assert len(item.steps) >= 3
            assert item.steps[0].number == 1
        # The known-code template gives concrete, non-technical instructions.
        meta_item = next(i for i in plan.items if i.source_code == "missing_meta_description")
        assert any("Meta description" in s.instruction for s in meta_item.steps)
        # Page URL inherited from the crawled page and injected into the steps.
        assert meta_item.page_url == "https://example.com/"
        assert any("https://example.com/" in s.instruction for s in meta_item.steps)

    def test_unknown_code_falls_back_to_category_template(self) -> None:
        issue = Issue(
            code="totally_custom_finding",
            title="Custom content finding",
            category=IssueCategory.CONTENT,
            severity=Severity.LOW,
        )
        plan = build_action_items("example.com", issues=[issue])
        assert plan.total == 1
        item = plan.items[0]
        assert item.severity == Severity.LOW
        assert len(item.steps) >= 2  # category fallback still gives guided steps

    def test_rank_quick_wins_reuse_reporting_tasks_logic(self) -> None:
        plan = build_action_items("example.com", rank_summary=_make_rank_summary())
        # Position 13 is on SERP page 2 -> quick win; position 45 excluded.
        assert plan.total == 1
        item = plan.items[0]
        assert item.source_code == "rank:quick_win"
        assert item.keyword == "best running shoes"

    def test_ids_stable_and_deduplicated(self) -> None:
        audit = _make_audit()
        located = [
            issue.model_copy(update={"url": "https://example.com/"})
            for issue in audit.pages[0].issues
        ]
        first = build_action_items("example.com", audit=audit, issues=located)
        second = build_action_items("example.com", audit=audit)
        assert first.total == second.total  # duplicates collapse onto same ids
        assert [i.id for i in first.items] == [i.id for i in second.items]


# ---------------------------------------------------------------------------
# Providers: deterministic mocks
# ---------------------------------------------------------------------------


class TestMockContentGenerator:
    def test_deterministic_outline_and_draft(self) -> None:
        gen = MockContentGenerator()
        a = gen.generate("local seo", topic="dental clinics")
        b = gen.generate("local seo", topic="dental clinics")
        assert a == b
        assert isinstance(a, BlogDraft)
        assert a.title.startswith("Local Seo")
        assert len(a.outline) == 5
        assert "local seo" in a.draft.lower()
        assert a.word_count > 50

    def test_empty_keyword_raises(self) -> None:
        with pytest.raises(ValueError):
            MockContentGenerator().generate("   ")


class TestMockCmsAdapter:
    def test_records_update_and_returns_stable_ref(self) -> None:
        cms = MockCmsAdapter()
        ref1 = cms.update_meta_tags("https://x.test/p", title="T", description="D")
        ref2 = cms.update_meta_tags("https://x.test/p", title="T2")
        assert ref1 == ref2  # ref derives from the URL only
        assert cms.updates["https://x.test/p"]["title"] == "T2"

    def test_missing_page_url_raises(self) -> None:
        with pytest.raises(ValueError):
            MockCmsAdapter().update_meta_tags("")


# ---------------------------------------------------------------------------
# Agentic execution queue
# ---------------------------------------------------------------------------


class _FailingGenerator:
    """Always raises. Exercises retry/failure handling."""

    def generate(self, keyword: str, topic: str | None = None) -> BlogDraft:
        raise RuntimeError("simulated generation failure")


class _FlakyGenerator:
    """Fails N times, then succeeds — exercises retry-until-success."""

    def __init__(self, fail_times: int = 1) -> None:
        self.fail_times = fail_times
        self.calls = 0

    def generate(self, keyword: str, topic: str | None = None) -> BlogDraft:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError(f"flaky failure #{self.calls}")
        return MockContentGenerator().generate(keyword, topic)


def _executor(**overrides) -> ActionExecutor:
    defaults = dict(
        content_generator=MockContentGenerator(),
        cms_adapter=MockCmsAdapter(),
        gbp_provider=MockGbpProvider(),
        citation_engine=CitationSyncEngine(build_mock_adapters()),
    )
    defaults.update(overrides)
    return ActionExecutor(**defaults)


class TestActionQueue:
    def test_enqueue_run_completes_blog_post(self) -> None:
        queue = ActionQueueService()
        action = queue.enqueue("org-a", ActionType.WRITE_BLOG_POST, {"keyword": "local seo"})
        assert action.status == ExecutionStatus.PENDING
        assert action.id == "act_000001"

        report = queue.run("org-a", _executor())

        assert report.executed == 1 and report.completed == 1 and report.failed == 0
        done = queue.get("org-a", action.id)
        assert done is not None
        assert done.status == ExecutionStatus.COMPLETED
        assert done.attempts == 1
        assert done.result and "draft" in done.result
        assert any(log.level == "info" for log in done.logs)

    def test_approval_mode_gates_execution(self) -> None:
        queue = ActionQueueService()
        action = queue.enqueue(
            "org-a", ActionType.WRITE_BLOG_POST, {"keyword": "seo"}, approval_required=True
        )
        assert action.status == ExecutionStatus.AWAITING_APPROVAL

        report = queue.run("org-a", _executor())
        assert report.skipped_awaiting_approval == 1 and report.executed == 0
        assert queue.get("org-a", action.id).status == ExecutionStatus.AWAITING_APPROVAL

        approved = queue.approve("org-a", action.id)
        assert approved is not None and approved.status == ExecutionStatus.PENDING
        report = queue.run("org-a", _executor())
        assert report.completed == 1
        # Re-approving a non-awaiting action is a caller error.
        with pytest.raises(ValueError):
            queue.approve("org-a", action.id)

    def test_retry_until_max_attempts_then_failed_with_logs(self) -> None:
        queue = ActionQueueService()
        queue.enqueue("org-a", ActionType.WRITE_BLOG_POST, {"keyword": "x"}, max_attempts=3)

        report = queue.run("org-a", _executor(content_generator=_FailingGenerator()))

        assert report.failed == 1
        action = queue.list("org-a")[0]
        assert action.status == ExecutionStatus.FAILED
        assert action.attempts == 3
        assert "simulated generation failure" in (action.last_error or "")
        assert sum(1 for log in action.logs if log.level == "error") == 3

    def test_flaky_provider_succeeds_on_retry(self) -> None:
        queue = ActionQueueService()
        queue.enqueue("org-a", ActionType.WRITE_BLOG_POST, {"keyword": "x"}, max_attempts=3)

        report = queue.run("org-a", _executor(content_generator=_FlakyGenerator(fail_times=1)))

        assert report.completed == 1
        action = queue.list("org-a")[0]
        assert action.status == ExecutionStatus.COMPLETED
        assert action.attempts == 2
        assert action.last_error is None

    def test_queue_is_org_scoped(self) -> None:
        queue = ActionQueueService()
        queue.enqueue("org-a", ActionType.WRITE_BLOG_POST, {"keyword": "a"})
        queue.enqueue("org-b", ActionType.WRITE_BLOG_POST, {"keyword": "b"})
        assert len(queue.list("org-a")) == 1
        assert len(queue.list("org-b")) == 1
        assert queue.get("org-a", queue.list("org-b")[0].id) is None
        # Running org-a leaves org-b untouched.
        queue.run("org-a", _executor())
        assert queue.list("org-b")[0].status == ExecutionStatus.PENDING

    def test_completed_actions_not_rerun(self) -> None:
        queue = ActionQueueService()
        queue.enqueue("org-a", ActionType.WRITE_BLOG_POST, {"keyword": "x"})
        queue.run("org-a", _executor())
        report = queue.run("org-a", _executor())
        assert report.executed == 0 and report.completed == 0


class TestActionExecutor:
    def test_update_meta_tags_uses_cms_adapter(self) -> None:
        cms = MockCmsAdapter()
        queue = ActionQueueService()
        queue.enqueue(
            "org-a",
            ActionType.UPDATE_META_TAGS,
            {"page_url": "https://x.test/p", "title": "New Title", "description": "New Desc"},
        )
        report = queue.run("org-a", _executor(cms_adapter=cms))
        assert report.completed == 1
        assert cms.updates["https://x.test/p"]["title"] == "New Title"
        assert queue.list("org-a")[0].result["cms_ref"].startswith("cms_")

    def test_publish_gbp_update_creates_post(self) -> None:
        gbp = MockGbpProvider()
        queue = ActionQueueService()
        queue.enqueue("org-a", ActionType.PUBLISH_GBP_UPDATE, {"summary": "New summer hours!"})
        report = queue.run("org-a", _executor(gbp_provider=gbp))
        assert report.completed == 1
        posts = gbp.list_posts("org-a")
        assert len(posts) == 1 and posts[0].summary == "New summer hours!"

    def test_publish_gbp_update_without_summary_fails(self) -> None:
        queue = ActionQueueService()
        queue.enqueue("org-a", ActionType.PUBLISH_GBP_UPDATE, {}, max_attempts=2)
        report = queue.run("org-a", _executor())
        assert report.failed == 1
        assert "summary" in (queue.list("org-a")[0].last_error or "")

    def test_sync_directory_listing_requires_then_uses_nap(self) -> None:
        engine = CitationSyncEngine(build_mock_adapters())
        queue = ActionQueueService()
        queue.enqueue("org-a", ActionType.SYNC_DIRECTORY_LISTING, {}, max_attempts=1)
        report = queue.run("org-a", _executor(citation_engine=engine))
        assert report.failed == 1  # no NAP configured yet

        engine.set_nap("org-a", NapRecord(name="Acme", address="1 Main St", phone="+15550001111"))
        queue.enqueue("org-a", ActionType.SYNC_DIRECTORY_LISTING, {"directory": "yelp"})
        report = queue.run("org-a", _executor(citation_engine=engine))
        assert report.completed == 1
        result = queue.list("org-a")[1].result
        assert result["sync"]["delivered"] == 1  # only yelp was synced


# ---------------------------------------------------------------------------
# Keyword mapping & cannibalization
# ---------------------------------------------------------------------------


_PAGES = [
    SitePage(
        url="https://ex.test/best-running-shoes",
        title="Best Running Shoes",
        content="The best running shoes for road runners, tested for comfort.",
    ),
    SitePage(
        url="https://ex.test/running-shoes-guide",
        title="Running Shoes Guide",
        content="A running shoes guide comparing cushioning and support for runners.",
    ),
    SitePage(
        url="https://ex.test/contact",
        title="Contact Us",
        content="Get in touch with our team by phone or email.",
    ),
]


class TestKeywordMapping:
    def test_assigns_keywords_to_most_relevant_pages(self) -> None:
        result = map_keywords(["running shoes", "contact"], _PAGES)
        by_kw = {a.keyword: a for a in result.assignments}
        assert by_kw["running shoes"].page_url in {
            "https://ex.test/best-running-shoes", "https://ex.test/running-shoes-guide"
        }
        assert by_kw["running shoes"].score > 0
        assert by_kw["contact"].page_url == "https://ex.test/contact"
        assert by_kw["running shoes"].alternatives  # runner-up page exposed

    def test_cannibalization_flagged_with_primary_and_actions(self) -> None:
        result = map_keywords(["running shoes", "contact"], _PAGES)
        assert len(result.cannibalization) == 1
        flag = result.cannibalization[0]
        assert flag.keyword == "running shoes"
        assert len(flag.competing_pages) == 2
        assert flag.primary_page == result.assignments[0].page_url
        assert flag.suggested_actions and any("301" in a for a in flag.suggested_actions)
        # 'contact' maps to a single page -> never flagged.
        assert all(f.keyword != "contact" for f in result.cannibalization)

    def test_irrelevant_keyword_is_unmapped(self) -> None:
        result = map_keywords(["quantum entanglement"], _PAGES)
        assert result.unmapped_keywords == ["quantum entanglement"]
        assert result.assignments[0].page_url is None

    def test_deterministic_output(self) -> None:
        kws = ["running shoes", "contact", "quantum entanglement"]
        assert map_keywords(kws, _PAGES) == map_keywords(kws, _PAGES)


# ---------------------------------------------------------------------------
# Content calendar
# ---------------------------------------------------------------------------


_CAL_KEYWORDS = [
    Keyword(keyword="running shoes", search_volume=2400, intent=SearchIntent.COMMERCIAL),
    Keyword(keyword="running shoes for beginners", search_volume=800),
    Keyword(keyword="marathon training plan", search_volume=500),
]


class TestContentCalendar:
    def test_dates_follow_cadence_and_clusters_order_by_volume(self) -> None:
        start = date(2026, 7, 13)
        calendar = build_content_calendar(_CAL_KEYWORDS, start=start, cadence=CalendarCadence.WEEKLY)
        assert calendar.total == 2  # "running shoes*" cluster + "marathon training"
        assert calendar.entries[0].publish_date == start
        assert calendar.entries[1].publish_date == date(2026, 7, 20)
        # Highest-volume cluster comes first, targeting its top keyword.
        assert calendar.entries[0].outline.target_keyword == "running shoes"
        assert calendar.entries[0].outline.intent == SearchIntent.COMMERCIAL
        assert "Best Running Shoes" in calendar.entries[0].title

    def test_outline_structure_and_supporting_keywords(self) -> None:
        calendar = build_content_calendar(_CAL_KEYWORDS, start=date(2026, 7, 13))
        outline = calendar.entries[0].outline
        assert outline.h1 == calendar.entries[0].title
        assert len(outline.headings) >= 3
        assert all(h.level == 2 for h in outline.headings)
        assert "running shoes for beginners" in outline.supporting_keywords

    def test_internal_links_come_from_mapped_pages(self) -> None:
        mapped = map_keywords([k.keyword for k in _CAL_KEYWORDS], _PAGES)
        calendar = build_content_calendar(
            _CAL_KEYWORDS, start=date(2026, 7, 13), assignments=mapped.assignments
        )
        links = calendar.entries[0].outline.internal_links
        assert links and all(link.startswith("https://ex.test/") for link in links)

    def test_max_entries_and_determinism(self) -> None:
        one = build_content_calendar(_CAL_KEYWORDS, start=date(2026, 7, 13), max_entries=1)
        assert one.total == 1
        a = build_content_calendar(_CAL_KEYWORDS, start=date(2026, 7, 13))
        b = build_content_calendar(_CAL_KEYWORDS, start=date(2026, 7, 13))
        assert a == b


# ---------------------------------------------------------------------------
# API routes (router mounted on a minimal app, spine-style)
# ---------------------------------------------------------------------------


def _assistant_app(test_engine) -> FastAPI:
    from app.api.routes_assistant import router as assistant_router

    app = FastAPI()

    def _get_session():
        with Session(test_engine) as s:
            yield s

    app.dependency_overrides[get_session] = _get_session
    register_exception_handlers(app)
    app.include_router(assistant_router)
    return app


class TestAssistantApi:
    def test_requires_authentication(self, test_engine) -> None:
        client = TestClient(_assistant_app(test_engine))
        assert client.get("/assistant/queue").status_code == 401
        assert client.post("/assistant/queue/run").status_code == 401

    def test_actions_plan_from_inline_issues(self, test_engine, make_auth) -> None:
        info = make_auth()
        client = TestClient(_assistant_app(test_engine))
        r = client.post(
            "/assistant/actions/plan",
            headers=info["headers"],
            json={
                "site": "example.com",
                "issues": [
                    {
                        "code": "missing_meta_description",
                        "title": "Missing meta description",
                        "category": "on_page",
                        "severity": "high",
                        "url": "https://example.com/",
                    }
                ],
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["items"][0]["steps"]

    def test_queue_lifecycle_over_api(self, test_engine, make_auth) -> None:
        info = make_auth()
        client = TestClient(_assistant_app(test_engine))
        headers = info["headers"]

        r = client.post(
            "/assistant/queue",
            headers=headers,
            json={"type": "write_blog_post", "params": {"keyword": "local seo"}},
        )
        assert r.status_code == 200
        action_id = r.json()["id"]
        assert r.json()["status"] == "pending"

        r = client.get("/assistant/queue", headers=headers)
        assert [a["id"] for a in r.json()] == [action_id]

        r = client.post("/assistant/queue/run", headers=headers)
        assert r.status_code == 200
        assert r.json()["completed"] == 1

        r = client.get("/assistant/queue", headers=headers)
        assert r.json()[0]["status"] == "completed"
        assert "draft" in r.json()[0]["result"]

    def test_approval_flow_and_errors_over_api(self, test_engine, make_auth) -> None:
        info = make_auth()
        client = TestClient(_assistant_app(test_engine))
        headers = info["headers"]

        r = client.post(
            "/assistant/queue",
            headers=headers,
            json={
                "type": "write_blog_post",
                "params": {"keyword": "seo"},
                "approval_required": True,
            },
        )
        action_id = r.json()["id"]
        assert r.json()["status"] == "awaiting_approval"

        r = client.post("/assistant/queue/run", headers=headers)
        assert r.json()["skipped_awaiting_approval"] == 1

        assert client.post("/assistant/queue/nope/approve", headers=headers).status_code == 404

        r = client.post(f"/assistant/queue/{action_id}/approve", headers=headers)
        assert r.status_code == 200 and r.json()["status"] == "pending"
        # Approving twice is a 400 (no longer awaiting approval).
        assert client.post(f"/assistant/queue/{action_id}/approve", headers=headers).status_code == 400

        r = client.post("/assistant/queue/run", headers=headers)
        assert r.json()["completed"] == 1

    def test_failed_run_with_overridden_provider(self, test_engine, make_auth) -> None:
        from app.api.routes_assistant import get_content_generator_dep

        info = make_auth()
        app = _assistant_app(test_engine)
        app.dependency_overrides[get_content_generator_dep] = lambda: _FailingGenerator()
        client = TestClient(app)
        headers = info["headers"]

        client.post(
            "/assistant/queue",
            headers=headers,
            json={"type": "write_blog_post", "params": {"keyword": "x"}, "max_attempts": 2},
        )
        r = client.post("/assistant/queue/run", headers=headers)
        assert r.json()["failed"] == 1
        action = client.get("/assistant/queue", headers=headers).json()[0]
        assert action["status"] == "failed" and action["attempts"] == 2

    def test_keyword_map_endpoint(self, test_engine, make_auth) -> None:
        info = make_auth()
        client = TestClient(_assistant_app(test_engine))
        r = client.post(
            "/assistant/keywords/map",
            headers=info["headers"],
            json={
                "keywords": ["running shoes", "contact"],
                "pages": [p.model_dump() for p in _PAGES],
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert len(body["assignments"]) == 2
        assert len(body["cannibalization"]) == 1

    def test_calendar_build_endpoint(self, test_engine, make_auth) -> None:
        info = make_auth()
        client = TestClient(_assistant_app(test_engine))
        r = client.post(
            "/assistant/calendar/build",
            headers=info["headers"],
            json={
                "keywords": [k.model_dump() for k in _CAL_KEYWORDS],
                "start_date": "2026-07-13",
                "cadence": "biweekly",
                "pages": [p.model_dump() for p in _PAGES],
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 2
        assert body["entries"][0]["publish_date"] == "2026-07-13"
        assert body["entries"][1]["publish_date"] == "2026-07-27"
        assert body["entries"][0]["outline"]["internal_links"]
