"""Models for the "Kit" assistant: guided action items, the agentic execution
queue, keyword-to-page mapping / cannibalization, and the content calendar."""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import Field

from app.models.common import AppModel, IssueCategory, SearchIntent, Severity


class FixStep(AppModel):
    """One numbered, plain-English step of a guided fix (no dev experience assumed)."""

    number: int
    instruction: str


class ActionItem(AppModel):
    """A prioritized, plain-English action item derived from an audit finding."""

    id: str
    title: str
    what_it_means: str = ""
    why_it_matters: str = ""
    category: IssueCategory = IssueCategory.ON_PAGE
    severity: Severity = Severity.MEDIUM
    priority_score: int = Field(default=0, ge=0)
    page_url: str | None = None
    keyword: str | None = None
    source_code: str = ""
    steps: list[FixStep] = []
    estimated_minutes: int = Field(default=15, ge=1)


class ActionItemPlan(AppModel):
    """Ordered set of :class:`ActionItem` for a site (highest priority first)."""

    site: str
    generated_at: datetime
    items: list[ActionItem] = []
    total: int = 0
    by_severity: dict[str, int] = {}


# ---------------------------------------------------------------------------
# Agentic execution queue
# ---------------------------------------------------------------------------


class ActionType(str, Enum):
    WRITE_BLOG_POST = "write_blog_post"
    UPDATE_META_TAGS = "update_meta_tags"
    PUBLISH_GBP_UPDATE = "publish_gbp_update"
    SYNC_DIRECTORY_LISTING = "sync_directory_listing"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    AWAITING_APPROVAL = "awaiting_approval"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionLogEntry(AppModel):
    """Structured log line captured while an action executes."""

    attempt: int
    level: str = "info"  # "info" | "error"
    message: str


class QueuedAction(AppModel):
    """An org-scoped executable action tracked through the execution loop."""

    id: str
    org_id: str
    type: ActionType
    params: dict[str, object] = Field(default_factory=dict)
    status: ExecutionStatus = ExecutionStatus.PENDING
    approval_required: bool = False
    attempts: int = 0
    max_attempts: int = Field(default=3, ge=1, le=10)
    result: dict[str, object] | None = None
    last_error: str | None = None
    logs: list[ExecutionLogEntry] = []
    created_at: datetime
    updated_at: datetime


class QueueRunReport(AppModel):
    """Outcome of one pass of the execution loop over an org's queue."""

    org_id: str
    executed: int = 0
    completed: int = 0
    failed: int = 0
    skipped_awaiting_approval: int = 0
    actions: list[QueuedAction] = []


class BlogDraft(AppModel):
    """Outline + draft produced by a :class:`ContentGenerator` provider."""

    keyword: str
    topic: str = ""
    title: str
    outline: list[str] = []
    draft: str = ""
    word_count: int = 0


# ---------------------------------------------------------------------------
# Keyword mapping & cannibalization
# ---------------------------------------------------------------------------


class SitePage(AppModel):
    """A site page (url + text) used as a keyword-mapping target."""

    url: str
    title: str = ""
    content: str = ""


class PageScore(AppModel):
    url: str
    score: float = 0.0


class KeywordAssignment(AppModel):
    """The most relevant page for a keyword, with runner-up alternatives."""

    keyword: str
    page_url: str | None = None
    score: float = 0.0
    alternatives: list[PageScore] = []


class CannibalizationFlag(AppModel):
    """Multiple pages competing for one keyword with close relevance scores."""

    keyword: str
    primary_page: str
    competing_pages: list[PageScore] = []
    suggested_actions: list[str] = []


class KeywordMapResult(AppModel):
    assignments: list[KeywordAssignment] = []
    cannibalization: list[CannibalizationFlag] = []
    unmapped_keywords: list[str] = []


# ---------------------------------------------------------------------------
# Content calendar
# ---------------------------------------------------------------------------


class CalendarCadence(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"

    @property
    def interval_days(self) -> int:
        return {"daily": 1, "weekly": 7, "biweekly": 14, "monthly": 30}[self.value]


class OutlineHeading(AppModel):
    level: int = Field(default=2, ge=1, le=3)
    text: str


class ArticleOutline(AppModel):
    """Structured article outline (H1/H2s, target keyword, intent, links)."""

    h1: str
    headings: list[OutlineHeading] = []
    target_keyword: str
    supporting_keywords: list[str] = []
    intent: SearchIntent = SearchIntent.INFORMATIONAL
    internal_links: list[str] = []


class CalendarEntry(AppModel):
    publish_date: date
    title: str
    cluster: str = ""
    outline: ArticleOutline


class ContentCalendar(AppModel):
    start_date: date
    cadence: CalendarCadence = CalendarCadence.WEEKLY
    entries: list[CalendarEntry] = []
    total: int = 0
