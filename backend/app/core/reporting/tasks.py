"""Action-plan / task generator.

Converts raw audit issues, failed on-page checks, and rank-tracking signals into a
single deduplicated, prioritized :class:`~app.models.reporting.ActionPlan`. Every
generated :class:`~app.models.reporting.Task` carries a stable, deterministic id
(sha256 of ``site|code|page``) so re-running against the same inputs yields the same
plan — no randomness, no network/IO calls.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from app.models.audit import CrawlResult
from app.models.common import Issue, IssueCategory, Severity
from app.models.keywords import RankTrackingSummary, TrackedKeyword
from app.models.onpage import CheckCategory, OnPageCheck, OnPageResult
from app.models.reporting import ActionPlan, AiReview, Effort, Task, TaskStatus

# Google SERP "page 2" window used to flag rank-based quick-win opportunities.
_PAGE_TWO_MIN = 11
_PAGE_TWO_MAX = 20

# Categories that are typically fixed with a markup/config tweak (cheap to ship).
_LOW_EFFORT_CATEGORIES = frozenset(
    {IssueCategory.ON_PAGE, IssueCategory.IMAGES, IssueCategory.STRUCTURED_DATA}
)
# Categories that usually require dev/infra work, migrations, or cross-page changes.
_HIGH_EFFORT_CATEGORIES = frozenset(
    {
        IssueCategory.TECHNICAL,
        IssueCategory.PERFORMANCE,
        IssueCategory.INTERNATIONAL,
        IssueCategory.SECURITY,
        IssueCategory.INDEXABILITY,
    }
)

_ONPAGE_CATEGORY_MAP: dict[CheckCategory, IssueCategory] = {
    CheckCategory.BASIC: IssueCategory.ON_PAGE,
    CheckCategory.ADDITIONAL: IssueCategory.ON_PAGE,
    CheckCategory.TITLE_READABILITY: IssueCategory.CONTENT,
    CheckCategory.CONTENT_READABILITY: IssueCategory.CONTENT,
}


def _make_task_id(site: str, code: str, page: str) -> str:
    """Stable, deterministic task id derived from ``site + code + page``."""
    raw = f"{site}|{code}|{page or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _effort_heuristic(category: IssueCategory, severity: Severity) -> Effort:
    """Cheap heuristic: category sets the base effort, severity can nudge it up."""
    if category in _HIGH_EFFORT_CATEGORIES:
        return Effort.HIGH if severity in (Severity.CRITICAL, Severity.HIGH) else Effort.MEDIUM
    if category in _LOW_EFFORT_CATEGORIES:
        return Effort.MEDIUM if severity == Severity.CRITICAL else Effort.LOW
    return Effort.MEDIUM


def _severity_from_weight(weight: int) -> Severity:
    """Map an :class:`OnPageCheck` weight (no inherent severity) onto ``Severity``."""
    if weight >= 5:
        return Severity.CRITICAL
    if weight >= 3:
        return Severity.HIGH
    if weight >= 2:
        return Severity.MEDIUM
    if weight >= 1:
        return Severity.LOW
    return Severity.INFO


def _build_ai_review(severity: Severity, has_basis: bool, basis: str) -> AiReview:
    """Lightweight explainability layer (Hike-style "AI Review").

    Flags critical-severity or under-specified tasks for human confirmation;
    everything else auto-passes, with confidence proportional to how concrete the
    underlying finding is.
    """
    if severity == Severity.CRITICAL:
        return AiReview(
            verdict="flag",
            reasoning=(
                "Critical-severity finding — recommend a human confirms scope and "
                "impact before this task is applied automatically."
            ),
            confidence=0.6,
        )
    if not has_basis:
        return AiReview(
            verdict="flag",
            reasoning="No specific recommendation text available; needs manual triage.",
            confidence=0.5,
        )
    trimmed = basis.strip()
    reasoning = f"Auto-generated from a rule-based finding: {trimmed[:160]}"
    return AiReview(verdict="pass", reasoning=reasoning, confidence=0.85)


def issue_to_task(site: str, issue: Issue) -> Task:
    """Convert a single audit :class:`Issue` into a :class:`Task`.

    ``issue.url`` (if set) becomes the task's ``page_url``; the task id is a stable
    hash of ``site + issue.code + issue.url`` so re-running the audit reproduces the
    same id and downstream status tracking / dedupe keeps working.
    """
    severity = issue.severity
    effort = _effort_heuristic(issue.category, severity)
    basis = issue.recommendation or issue.description
    has_basis = bool(basis.strip())
    description = basis or issue.title
    review = _build_ai_review(severity, has_basis, basis)

    return Task(
        id=_make_task_id(site, issue.code, issue.url or ""),
        title=issue.title,
        description=description,
        category=issue.category,
        priority=severity,
        status=TaskStatus.TODO,
        page_url=issue.url,
        keyword=None,
        impact=severity.weight,
        effort=effort,
        ai_review=review,
    )


def _task_from_onpage_check(site: str, result: OnPageResult, check: OnPageCheck) -> Task:
    """Convert one failed :class:`OnPageCheck` into a :class:`Task`."""
    severity = _severity_from_weight(check.weight)
    category = _ONPAGE_CATEGORY_MAP.get(check.category, IssueCategory.ON_PAGE)
    effort = _effort_heuristic(category, severity)
    has_message = bool(check.message.strip())
    description = check.message or f"On-page check '{check.label}' failed."
    review = _build_ai_review(severity, has_message, check.message)

    return Task(
        id=_make_task_id(site, f"onpage:{check.code}", result.target_keyword),
        title=f"Fix on-page issue: {check.label}",
        description=description,
        category=category,
        priority=severity,
        status=TaskStatus.TODO,
        page_url=None,
        keyword=result.target_keyword,
        impact=severity.weight,
        effort=effort,
        ai_review=review,
    )


def _rank_quick_win_task(site: str, keyword: TrackedKeyword) -> Task | None:
    """Flag a keyword ranking on SERP page 2 as a low-effort quick-win opportunity."""
    position = keyword.current_position
    if position is None or not (_PAGE_TWO_MIN <= position <= _PAGE_TWO_MAX):
        return None

    severity = Severity.HIGH if position <= 15 else Severity.MEDIUM
    reasoning = (
        f"'{keyword.keyword}' currently ranks #{position} on {keyword.domain} "
        "(SERP page 2). Page-2 keywords are typically the fastest path to a top-10 "
        "ranking via internal linking, content refreshes, or on-page tweaks."
    )
    review = AiReview(verdict="pass", reasoning=reasoning, confidence=0.75 if position <= 15 else 0.65)

    return Task(
        id=_make_task_id(site, "rank:quick_win", keyword.keyword),
        title=f"Quick win: push '{keyword.keyword}' from page 2 to page 1",
        description=(
            f"Ranking #{position} (search volume {keyword.search_volume}). Prioritize "
            "content refresh, internal linking, and on-page optimization to convert "
            "this into a top-10 ranking."
        ),
        category=IssueCategory.CONTENT,
        priority=severity,
        status=TaskStatus.TODO,
        page_url=None,
        keyword=keyword.keyword,
        impact=severity.weight,
        effort=Effort.LOW,
        ai_review=review,
    )


def generate_action_plan(
    site: str,
    audit: CrawlResult | None = None,
    onpage_results: list[OnPageResult] | None = None,
    rank_summary: RankTrackingSummary | None = None,
) -> ActionPlan:
    """Build a deduplicated, prioritized :class:`ActionPlan` for ``site``.

    Sources (all optional, independently combinable):
      * ``audit`` — every :class:`Issue` on every crawled page becomes a task.
      * ``onpage_results`` — every failed :class:`OnPageCheck` becomes a task.
      * ``rank_summary`` — keywords ranking on SERP page 2 (positions 11-20) become
        low-effort "quick win" tasks.

    Tasks are deduplicated by id and sorted by ``(priority weight desc, impact desc)``.
    """
    tasks: list[Task] = []

    if audit is not None:
        for page in audit.pages:
            for issue in page.issues:
                located = issue if issue.url else issue.model_copy(update={"url": page.url})
                tasks.append(issue_to_task(site, located))

    if onpage_results:
        for result in onpage_results:
            for check in result.checks:
                if not check.passed:
                    tasks.append(_task_from_onpage_check(site, result, check))

    if rank_summary is not None:
        for keyword in rank_summary.keywords:
            quick_win = _rank_quick_win_task(site, keyword)
            if quick_win is not None:
                tasks.append(quick_win)

    deduped: dict[str, Task] = {}
    for task in tasks:
        deduped.setdefault(task.id, task)
    unique_tasks = list(deduped.values())
    unique_tasks.sort(key=lambda t: (-t.priority.weight, -t.impact))

    by_priority: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for task in unique_tasks:
        by_priority[task.priority.value] = by_priority.get(task.priority.value, 0) + 1
        by_status[task.status.value] = by_status.get(task.status.value, 0) + 1

    return ActionPlan(
        site=site,
        generated_at=datetime.now(timezone.utc),
        tasks=unique_tasks,
        total=len(unique_tasks),
        by_priority=by_priority,
        by_status=by_status,
    )
