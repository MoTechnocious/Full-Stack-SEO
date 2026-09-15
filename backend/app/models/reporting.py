"""Models for action plans / tasks and white-label agency reporting (HikeSEO style)."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from app.models.common import AppModel, IssueCategory, Severity


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FLAGGED = "flagged"


class Effort(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AiReview(AppModel):
    """Explainability layer over an auto-generated task (Hike 'AI Review' style)."""

    verdict: str = "pass"  # "pass" | "flag"
    reasoning: str = ""
    confidence: float = 0.8


class Task(AppModel):
    id: str
    title: str
    description: str = ""
    category: IssueCategory = IssueCategory.ON_PAGE
    priority: Severity = Severity.MEDIUM
    status: TaskStatus = TaskStatus.TODO
    page_url: str | None = None
    keyword: str | None = None
    impact: int = Field(default=3, ge=1, le=5)
    effort: Effort = Effort.MEDIUM
    ai_review: AiReview | None = None


class ActionPlan(AppModel):
    site: str
    generated_at: datetime
    tasks: list[Task] = []
    total: int = 0
    by_priority: dict[str, int] = {}
    by_status: dict[str, int] = {}


class WhiteLabelBranding(AppModel):
    agency_name: str = "MySEOapp"
    logo_url: str | None = None
    primary_color: str = "#4f46e5"
    accent_color: str = "#22d3ee"
    footer_text: str = ""
    agent_name: str = "Hikebot"
    agent_icon_url: str | None = None
    contact_email: str | None = None


class ReportSection(AppModel):
    title: str
    type: str  # "summary" | "rankings" | "audit" | "tasks" | "keywords" | "chart"
    summary: str = ""
    data: dict[str, object] = Field(default_factory=dict)


class Report(AppModel):
    report_id: str
    site: str
    period_start: str
    period_end: str
    generated_at: datetime
    branding: WhiteLabelBranding = WhiteLabelBranding()
    sections: list[ReportSection] = []
    headline_metrics: dict[str, object] = Field(default_factory=dict)
