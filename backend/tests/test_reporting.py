"""Tests for the action-plan generator and white-label reporting engine."""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.reporting.reports import build_report, render_report_html
from app.core.reporting.tasks import generate_action_plan, issue_to_task
from app.core.reporting.whitelabel import apply_branding
from app.models.audit import CrawlConfig, CrawlResult, CrawlSummary, PageAuditResult
from app.models.common import Issue, IssueCategory, Severity
from app.models.keywords import RankTrackingSummary, TrackedKeyword
from app.models.onpage import CheckCategory, OnPageCheck, OnPageResult
from app.models.reporting import TaskStatus, WhiteLabelBranding


def _make_audit(site_url: str = "https://example.com") -> CrawlResult:
    """A small, deterministic 2-page crawl with issues of mixed severity."""
    config = CrawlConfig(start_url=site_url)
    page1 = PageAuditResult(
        url=f"{site_url}/",
        final_url=f"{site_url}/",
        status_code=200,
        score=62,
        issues=[
            Issue(
                code="missing_meta_description",
                title="Missing meta description",
                description="The page has no meta description.",
                category=IssueCategory.ON_PAGE,
                severity=Severity.HIGH,
                recommendation="Add a unique 150-160 character meta description.",
                url=f"{site_url}/",
            ),
            Issue(
                code="thin_content",
                title="Thin content",
                description="Page has very little text content.",
                category=IssueCategory.CONTENT,
                severity=Severity.MEDIUM,
                recommendation="Expand content to at least 600 words.",
                url=f"{site_url}/",
            ),
        ],
    )
    page2 = PageAuditResult(
        url=f"{site_url}/about",
        final_url=f"{site_url}/about",
        status_code=200,
        score=40,
        issues=[
            Issue(
                code="broken_link",
                title="Broken internal link",
                description="A link on this page returns a 404.",
                category=IssueCategory.LINKS,
                severity=Severity.CRITICAL,
                recommendation="Fix or remove the broken link.",
                url=f"{site_url}/about",
            ),
        ],
    )
    summary = CrawlSummary(
        total_pages=2,
        by_status_class={"2xx": 2},
        by_severity={"critical": 1, "high": 1, "medium": 1},
        indexable_pages=2,
        non_indexable_pages=0,
        pages_with_issues=2,
        avg_score=51.0,
        broken_links_total=1,
        missing_titles=0,
        duplicate_titles=0,
        missing_meta_descriptions=1,
    )
    return CrawlResult(
        crawl_id="crawl-1",
        start_url=site_url,
        config=config,
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        pages=[page1, page2],
        summary=summary,
        top_issues=[page2.issues[0], page1.issues[0]],
    )


def _make_rank_summary(domain: str = "example.com") -> RankTrackingSummary:
    keywords = [
        TrackedKeyword(
            keyword="best running shoes",
            domain=domain,
            search_volume=2400,
            current_position=13,
            previous_position=15,
            best_position=13,
        ),
        TrackedKeyword(
            keyword="running shoes for beginners",
            domain=domain,
            search_volume=800,
            current_position=3,
            previous_position=5,
            best_position=3,
        ),
        TrackedKeyword(
            keyword="marathon training plan",
            domain=domain,
            search_volume=500,
            current_position=45,
            previous_position=40,
            best_position=30,
        ),
    ]
    return RankTrackingSummary(
        domain=domain,
        total_keywords=len(keywords),
        avg_position=20.3,
        improved=1,
        declined=1,
        unchanged=0,
        top3=1,
        top10=1,
        visibility_score=42.5,
        keywords=keywords,
    )


def _make_onpage_result(keyword: str = "best running shoes") -> OnPageResult:
    checks = [
        OnPageCheck(
            code="title_has_keyword",
            label="Title contains focus keyword",
            category=CheckCategory.BASIC,
            passed=False,
            weight=3,
            message="Add the focus keyword to the page title.",
        ),
        OnPageCheck(
            code="meta_length_ok",
            label="Meta description length",
            category=CheckCategory.ADDITIONAL,
            passed=True,
            weight=1,
            message="Meta description length is within range.",
        ),
    ]
    return OnPageResult(
        target_keyword=keyword, score=55, grade="D", passed_count=1, total_count=2, checks=checks
    )


class TestGenerateActionPlan:
    def test_tasks_non_empty_and_sorted_with_ai_review(self) -> None:
        plan = generate_action_plan(site="example.com", audit=_make_audit())

        assert plan.total > 0
        assert len(plan.tasks) == plan.total
        assert all(task.ai_review is not None for task in plan.tasks)

        weights = [task.priority.weight for task in plan.tasks]
        assert weights == sorted(weights, reverse=True)

        assert sum(plan.by_priority.values()) == plan.total

    def test_dedupe_by_id_and_rank_quick_wins(self) -> None:
        plan = generate_action_plan(
            site="example.com", audit=_make_audit(), rank_summary=_make_rank_summary()
        )
        ids = [t.id for t in plan.tasks]
        assert len(ids) == len(set(ids))
        # "best running shoes" sits on page 2 (position 13) -> quick-win task expected.
        assert any(t.keyword == "best running shoes" for t in plan.tasks)
        # "marathon training plan" at position 45 is not on page 2 -> excluded.
        assert all(t.keyword != "marathon training plan" for t in plan.tasks)

    def test_issue_to_task_helper(self) -> None:
        issue = Issue(
            code="missing_h1",
            title="Missing H1",
            category=IssueCategory.ON_PAGE,
            severity=Severity.LOW,
            url="https://example.com/x",
        )
        task = issue_to_task("example.com", issue)
        assert task.priority == Severity.LOW
        assert task.impact == Severity.LOW.weight
        assert task.status == TaskStatus.TODO
        assert task.ai_review is not None

    def test_onpage_failed_checks_become_tasks(self) -> None:
        plan = generate_action_plan(site="example.com", onpage_results=[_make_onpage_result()])
        assert plan.total == 1  # only the failed check becomes a task
        assert plan.tasks[0].keyword == "best running shoes"
        assert plan.tasks[0].ai_review is not None


class TestApplyBranding:
    def test_merge_partial_overrides(self) -> None:
        branding = apply_branding({"agency_name": "Acme SEO", "primary_color": "#ff0000"})
        assert branding.agency_name == "Acme SEO"
        assert branding.primary_color == "#ff0000"
        # Unset fields keep model defaults.
        defaults = WhiteLabelBranding()
        assert branding.accent_color == defaults.accent_color
        assert branding.agent_name == defaults.agent_name

    def test_none_and_model_input_never_error(self) -> None:
        assert apply_branding(None) == WhiteLabelBranding()
        existing = WhiteLabelBranding(agency_name="Existing Co")
        assert apply_branding(existing).agency_name == "Existing Co"
        # A partially-invalid dict must never raise; valid fields still apply.
        weird = apply_branding(
            {"agency_name": "Ok Co", "primary_color": 12345, "unknown_field": "x"}
        )
        assert weird.agency_name == "Ok Co"


class TestBuildReportAndHtml:
    def test_build_report_sections_and_headline_metrics(self) -> None:
        report = build_report(
            site="example.com",
            period_start="2026-06-01",
            period_end="2026-06-30",
            audit=_make_audit(),
            rank_summary=_make_rank_summary(),
        )
        assert len(report.sections) >= 3
        assert "health_score" in report.headline_metrics
        assert report.headline_metrics["health_score"] is not None
        section_types = {s.type for s in report.sections}
        assert {"summary", "audit", "rankings"}.issubset(section_types)

    def test_render_report_html_branding(self) -> None:
        branding = apply_branding({"agency_name": "Acme SEO", "primary_color": "#ff0000"})
        report = build_report(
            site="example.com",
            period_start="2026-06-01",
            period_end="2026-06-30",
            branding=branding,
            audit=_make_audit(),
        )
        html_out = render_report_html(report)
        assert "Acme SEO" in html_out
        assert "SEO_" not in html_out

    def test_render_report_html_escapes_injected_script(self) -> None:
        malicious_site = "<script>alert('xss')</script>"
        report = build_report(
            site=malicious_site, period_start="2026-06-01", period_end="2026-06-30"
        )
        html_out = render_report_html(report)
        assert "<script>" not in html_out
        assert "&lt;script&gt;" in html_out
