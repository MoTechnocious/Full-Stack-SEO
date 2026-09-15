"""Models for the v2 AI Answer-Engine Visibility Tracker (PRODUCT_SPEC §8).

Scheduled, managed, tier-gated tracking on top of the one-shot GEO scans:
org-scoped tracker configs (named prompt sets + target market/language +
competitors + refresh cadence), per-run parsed answers, Visibility Score /
Share-of-Voice rollups with run-over-run deltas, and the Mention-Gap report.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from app.models.common import AppModel
from app.models.geo import Citation, SentimentLabel


class TrackerEngine(str, Enum):
    """Answer engines the v2 tracker queries.

    This is the tracker's own enum (per spec: ChatGPT, Perplexity, Gemini,
    Google AI Overviews, Google AI Mode). It extends beyond
    :class:`app.models.geo.AnswerEngine`, which lacks ``google_ai_mode``.
    """

    CHATGPT = "chatgpt"
    PERPLEXITY = "perplexity"
    GEMINI = "gemini"
    GOOGLE_AI_OVERVIEWS = "google_ai_overviews"
    GOOGLE_AI_MODE = "google_ai_mode"


class RefreshCadence(str, Enum):
    """How often a tracker config is refreshed (plan-gated)."""

    DAILY = "daily"
    WEEKLY = "weekly"


# ---------------------------------------------------------------------------
# Tracker configs (managed prompt sets)
# ---------------------------------------------------------------------------


class TrackerConfigCreate(AppModel):
    name: str
    brand: str
    prompts: list[str] = []
    competitors: list[str] = []
    engines: list[TrackerEngine] = []  # empty -> the plan's full allowed engine set
    market: str = "global"
    language: str = "en"
    own_domain: str | None = None  # None -> derived from the brand name
    refresh_cadence: RefreshCadence = RefreshCadence.WEEKLY


class TrackerConfigUpdate(AppModel):
    """Partial update; ``None`` means "keep the current value"."""

    name: str | None = None
    brand: str | None = None
    prompts: list[str] | None = None
    competitors: list[str] | None = None
    engines: list[TrackerEngine] | None = None  # [] -> reset to the plan default
    market: str | None = None
    language: str | None = None
    own_domain: str | None = None
    refresh_cadence: RefreshCadence | None = None


class TrackerConfig(AppModel):
    id: str
    name: str
    brand: str
    prompts: list[str]
    competitors: list[str] = []
    engines: list[TrackerEngine]
    market: str = "global"
    language: str = "en"
    own_domain: str
    refresh_cadence: RefreshCadence = RefreshCadence.WEEKLY
    created_at: datetime
    last_run_at: datetime | None = None


class DueConfig(AppModel):
    """A config due for a scheduled refresh (returned by the ops endpoint)."""

    config_id: str
    name: str
    brand: str
    refresh_cadence: RefreshCadence
    last_run_at: datetime | None = None  # None -> never run


# ---------------------------------------------------------------------------
# Parsed answers
# ---------------------------------------------------------------------------


class TrackerAnswer(AppModel):
    """One engine answer for one prompt, parsed for brand/competitor signals."""

    engine: TrackerEngine
    prompt: str
    text: str = ""
    ranked_list: list[str] = []
    citations: list[Citation] = []
    brand_mentioned: bool = False
    brand_mentions: int = 0  # whole-phrase text mentions
    brand_position: int | None = None  # 1-based position within the answer's ranked list
    competitors_mentioned: list[str] = []  # sorted, distinct
    sentiment_label: SentimentLabel = SentimentLabel.NEUTRAL
    sentiment_score: float = Field(default=0.0, ge=-1.0, le=1.0)


# ---------------------------------------------------------------------------
# Metrics rollups
# ---------------------------------------------------------------------------


class RollupMetrics(AppModel):
    """Aggregates for one engine (or overall). See ``app.core.aitracker.engine``
    for the exact deterministic formulas."""

    prompts_total: int = 0
    prompts_mentioned: int = 0
    mention_rate: float = 0.0  # prompts_mentioned / prompts_total
    avg_position: float | None = None  # mean 1-based rank where present (1 = best)
    position_score: float = Field(default=0.0, ge=0.0, le=1.0)  # mean of 1/rank (0 if absent)
    citation_share: float = Field(default=0.0, ge=0.0, le=1.0)  # own-domain / all citations
    visibility_score: float = Field(default=0.0, ge=0.0, le=100.0)  # weighted blend, 0-100
    share_of_voice: float = 0.0  # brand mentions / (brand + competitor mentions)
    competitor_share_of_voice: dict[str, float] = {}
    avg_sentiment: float = Field(default=0.0, ge=-1.0, le=1.0)
    sentiment_label: SentimentLabel = SentimentLabel.NEUTRAL
    # Run-over-run trend deltas (None on the first run).
    visibility_score_delta: float | None = None
    share_of_voice_delta: float | None = None
    mention_rate_delta: float | None = None
    avg_position_delta: float | None = None  # positive = improvement (closer to #1)


class EngineRollup(RollupMetrics):
    engine: TrackerEngine


class VisibilityRollup(AppModel):
    """The per-run metrics rollup (latest one served by GET .../visibility)."""

    config_id: str
    brand: str
    run_at: datetime
    engines: list[EngineRollup] = []
    overall: RollupMetrics


# ---------------------------------------------------------------------------
# Mention-Gap report
# ---------------------------------------------------------------------------


class MentionGapEntry(AppModel):
    """A prompt where competitors are mentioned but the brand is not."""

    prompt: str
    gap_engines: list[TrackerEngine] = []  # engines where the gap occurs
    competitors_mentioned: list[str] = []  # sorted, distinct across gap engines
    opportunity_score: float = 0.0  # gap engines x distinct competitors


class MentionGapReport(AppModel):
    config_id: str
    brand: str
    run_at: datetime
    total_prompts: int = 0
    entries: list[MentionGapEntry] = []  # ranked by opportunity_score desc


# ---------------------------------------------------------------------------
# Run report
# ---------------------------------------------------------------------------


class TrackerRunReport(AppModel):
    """Everything one tracker run produced: answers, rollup, mention gap."""

    config_id: str
    brand: str
    run_at: datetime
    engines: list[TrackerEngine] = []
    answers: list[TrackerAnswer] = []
    rollup: VisibilityRollup
    mention_gap: MentionGapReport
