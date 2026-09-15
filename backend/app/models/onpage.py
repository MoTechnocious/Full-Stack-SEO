"""Models for on-page analysis and content optimization (Rank Math + Surfer style)."""
from __future__ import annotations

from enum import Enum

from pydantic import Field

from app.models.common import AppModel, Issue


class CheckCategory(str, Enum):
    BASIC = "basic_seo"
    ADDITIONAL = "additional_seo"
    TITLE_READABILITY = "title_readability"
    CONTENT_READABILITY = "content_readability"


class OnPageRequest(AppModel):
    """Input for the rule-based on-page analyzer.

    Provide either raw ``html`` or the already-extracted fields. ``target_keyword``
    drives keyword-placement checks.
    """

    url: str | None = None
    html: str | None = None
    title: str | None = None
    meta_description: str | None = None
    content: str | None = None  # plain-text body if html not supplied
    target_keyword: str
    secondary_keywords: list[str] = []


class OnPageCheck(AppModel):
    code: str
    label: str
    category: CheckCategory
    passed: bool
    weight: int = 1
    message: str = ""


class OnPageResult(AppModel):
    target_keyword: str
    score: int = 0                 # 0-100 weighted
    grade: str = "F"
    passed_count: int = 0
    total_count: int = 0
    checks: list[OnPageCheck] = []
    issues: list[Issue] = []
    category_scores: dict[str, int] = {}


class TermStatus(str, Enum):
    UNDER = "under"
    OPTIMAL = "optimal"
    OVER = "over"


class TermTarget(AppModel):
    """A recommended usage band for a term, derived from SERP competitors."""

    term: str
    current_count: int = 0
    recommended_min: int = 0
    recommended_max: int = 0
    status: TermStatus = TermStatus.UNDER
    in_headings: bool = False
    importance: float = 1.0


class ContentEditorRequest(AppModel):
    target_keyword: str
    content: str = ""
    country: str = "us"
    secondary_keywords: list[str] = []
    competitor_word_counts: list[int] = []  # optional; if empty, derived from SERP provider


class ContentScore(AppModel):
    """Surfer-style dual score with actionable term/structure targets."""

    target_keyword: str
    content_score: int = 0          # blended 0-100
    seo_score: int = 0
    ai_search_score: int | None = None
    word_count: int = 0
    word_count_target_min: int = 0
    word_count_target_max: int = 0
    headings_count: int = 0
    headings_target: int = 0
    images_count: int = 0
    images_target: int = 0
    term_targets: list[TermTarget] = []
    missing_terms: list[str] = []
    overused_terms: list[str] = []
    suggestions: list[str] = []


# ---- Schema.org structured-data generator (Rank Math schema generator style) ----

class SchemaType(str, Enum):
    ARTICLE = "Article"
    PRODUCT = "Product"
    FAQ = "FAQPage"
    HOW_TO = "HowTo"
    LOCAL_BUSINESS = "LocalBusiness"
    ORGANIZATION = "Organization"
    BREADCRUMB = "BreadcrumbList"
    EVENT = "Event"
    RECIPE = "Recipe"
    PERSON = "Person"
    WEBSITE = "WebSite"
    VIDEO = "VideoObject"


class SchemaRequest(AppModel):
    schema_type: SchemaType
    fields: dict[str, object] = Field(default_factory=dict)


class SchemaResult(AppModel):
    schema_type: SchemaType
    json_ld: dict[str, object]
    script_tag: str
    warnings: list[str] = []
