"""Models for keyword research, SERP analysis, and rank tracking (HikeSEO style)."""
from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import Field

from app.models.common import AppModel, Device, SearchIntent


class SerpFeature(str, Enum):
    FEATURED_SNIPPET = "featured_snippet"
    PEOPLE_ALSO_ASK = "people_also_ask"
    LOCAL_PACK = "local_pack"
    IMAGE_PACK = "image_pack"
    VIDEO = "video"
    SHOPPING = "shopping"
    AI_OVERVIEW = "ai_overview"
    KNOWLEDGE_PANEL = "knowledge_panel"
    SITELINKS = "sitelinks"
    TOP_STORIES = "top_stories"


class Keyword(AppModel):
    keyword: str
    search_volume: int = 0
    difficulty: int = Field(default=0, ge=0, le=100)
    cpc: float = 0.0
    competition: float = Field(default=0.0, ge=0.0, le=1.0)
    intent: SearchIntent = SearchIntent.INFORMATIONAL
    parent_topic: str | None = None
    serp_features: list[SerpFeature] = []


class KeywordCluster(AppModel):
    name: str
    keywords: list[Keyword] = []
    total_volume: int = 0
    avg_difficulty: float = 0.0


class KeywordResearchRequest(AppModel):
    seed: str
    country: str = "us"
    language: str = "en"
    limit: int = Field(default=50, ge=1, le=1000)
    include_questions: bool = True


class KeywordResearchResult(AppModel):
    seed: str
    country: str = "us"
    keywords: list[Keyword] = []
    clusters: list[KeywordCluster] = []
    total_keywords: int = 0


class SerpResultItem(AppModel):
    position: int
    url: str
    domain: str = ""
    title: str = ""
    snippet: str = ""
    word_count: int | None = None
    backlinks: int | None = None


class SerpAnalysis(AppModel):
    keyword: str
    country: str = "us"
    device: Device = Device.DESKTOP
    results: list[SerpResultItem] = []
    features: list[SerpFeature] = []
    avg_word_count: int = 0
    avg_backlinks: int = 0
    difficulty: int = 0


class RankPoint(AppModel):
    day: date
    position: int | None = None  # None = not ranking in tracked window
    url: str | None = None


class TrackedKeyword(AppModel):
    keyword: str
    domain: str
    country: str = "us"
    device: Device = Device.DESKTOP
    search_volume: int = 0
    current_position: int | None = None
    previous_position: int | None = None
    best_position: int | None = None
    history: list[RankPoint] = []

    @property
    def delta(self) -> int | None:
        if self.current_position is None or self.previous_position is None:
            return None
        # Positive delta = improvement (moved closer to #1)
        return self.previous_position - self.current_position


class RankTrackingSummary(AppModel):
    domain: str
    country: str = "us"
    total_keywords: int = 0
    avg_position: float = 0.0
    improved: int = 0
    declined: int = 0
    unchanged: int = 0
    top3: int = 0
    top10: int = 0
    visibility_score: float = 0.0  # 0-100 weighted by volume & position
    keywords: list[TrackedKeyword] = []
