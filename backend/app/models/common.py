"""Shared enums, base models, and scoring helpers used across all domains."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class AppModel(BaseModel):
    """Base model: allow population by field name or alias, ignore unknown input."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class Severity(str, Enum):
    """Issue / task severity, ordered from most to least urgent."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @property
    def weight(self) -> int:
        return {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}[self.value]


class IssueCategory(str, Enum):
    """Buckets used to group audit findings and tasks."""

    TECHNICAL = "technical"
    ON_PAGE = "on_page"
    CONTENT = "content"
    LINKS = "links"
    IMAGES = "images"
    INDEXABILITY = "indexability"
    PERFORMANCE = "performance"
    STRUCTURED_DATA = "structured_data"
    INTERNATIONAL = "international"
    SECURITY = "security"
    MOBILE = "mobile"
    LOCAL = "local"


class Device(str, Enum):
    DESKTOP = "desktop"
    MOBILE = "mobile"


class SearchIntent(str, Enum):
    INFORMATIONAL = "informational"
    NAVIGATIONAL = "navigational"
    COMMERCIAL = "commercial"
    TRANSACTIONAL = "transactional"


class Indexability(str, Enum):
    INDEXABLE = "indexable"
    NON_INDEXABLE = "non_indexable"


class Issue(AppModel):
    """A single, actionable finding produced by any analyzer."""

    code: str
    title: str
    description: str = ""
    category: IssueCategory = IssueCategory.TECHNICAL
    severity: Severity = Severity.MEDIUM
    recommendation: str = ""
    url: str | None = None
    details: dict[str, object] = {}


def grade_from_score(score: int | float) -> str:
    """Map a 0-100 score to a letter grade (A-F), matching common SEO UIs."""
    s = max(0.0, min(100.0, float(score)))
    if s >= 90:
        return "A"
    if s >= 80:
        return "B"
    if s >= 70:
        return "C"
    if s >= 60:
        return "D"
    if s >= 50:
        return "E"
    return "F"


def status_label(score: int | float) -> str:
    """Human status label used by dashboards (green/amber/red style)."""
    s = float(score)
    if s >= 80:
        return "good"
    if s >= 50:
        return "needs_improvement"
    return "poor"
