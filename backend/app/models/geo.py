"""Models for GEO (Generative Engine Optimization): cross-LLM visibility, prompt
analytics, citation/source mapping, sentiment profiling, and AI readiness audits."""
from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import Field

from app.models.common import AppModel, Issue


class AnswerEngine(str, Enum):
    """Generative answer engines tracked for brand visibility."""

    CHATGPT = "chatgpt"
    CLAUDE = "claude"
    PERPLEXITY = "perplexity"
    COPILOT = "copilot"
    GEMINI = "gemini"
    GOOGLE_AI_OVERVIEWS = "google_ai_overviews"


class FunnelStage(str, Enum):
    """Marketing funnel stage of a tracked conversational prompt."""

    TOFU = "tofu"  # top of funnel: discovery / education
    MOFU = "mofu"  # middle of funnel: comparison / evaluation
    BOFU = "bofu"  # bottom of funnel: purchase-intent


class SentimentLabel(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class DomainCategory(str, Enum):
    """Classification of a cited source domain for trust analysis."""

    COMMUNITY = "community"          # reddit.com and friends
    ENCYCLOPEDIA = "encyclopedia"    # wikipedia.org
    REVIEW_PLATFORM = "review_platform"  # g2.com, capterra.com, trustpilot.com
    QA_FORUM = "qa_forum"            # quora.com, stackexchange
    NEWS = "news"
    BLOG = "blog"
    OWN_DOMAIN = "own_domain"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Engine answers (provider output)
# ---------------------------------------------------------------------------


class Citation(AppModel):
    """A single URL cited by an answer engine."""

    url: str
    domain: str = ""
    title: str = ""


class EngineAnswer(AppModel):
    """One synthesized answer from one engine for one prompt."""

    engine: AnswerEngine
    prompt: str
    text: str = ""
    ranked_list: list[str] = []  # brand/competitor names in recommendation order
    citations: list[Citation] = []


# ---------------------------------------------------------------------------
# Cross-LLM visibility
# ---------------------------------------------------------------------------


class VisibilityScanRequest(AppModel):
    brand: str
    competitors: list[str] = []
    prompts: list[str] = []  # empty -> use the org's tracked prompt library
    engines: list[AnswerEngine] = []  # empty -> all engines


class VisibilityMetrics(AppModel):
    """Brand visibility aggregates for one engine (or overall)."""

    prompts_scanned: int = 0
    mentions: int = 0
    mention_frequency: float = 0.0  # share of prompts where the brand is mentioned
    share_of_voice: float = 0.0     # brand mentions / (brand + competitor mentions)
    avg_position: float | None = None  # mean rank in generated lists (1 = best)
    mention_frequency_delta: float | None = None
    share_of_voice_delta: float | None = None
    avg_position_delta: float | None = None  # positive = improvement (closer to #1)


class EngineVisibility(VisibilityMetrics):
    engine: AnswerEngine


class VisibilityReport(AppModel):
    brand: str
    competitors: list[str] = []
    scanned_on: date
    engines: list[EngineVisibility] = []
    overall: VisibilityMetrics
    competitor_share_of_voice: dict[str, float] = {}
    answers: list[EngineAnswer] = []


# ---------------------------------------------------------------------------
# Prompt analytics & library
# ---------------------------------------------------------------------------


class TrackedPrompt(AppModel):
    id: str
    text: str
    funnel_stage: FunnelStage = FunnelStage.TOFU
    intent_tags: list[str] = []
    volume_estimate: int = 0
    created_on: date


class PromptCreate(AppModel):
    text: str
    funnel_stage: FunnelStage | None = None  # None -> classified deterministically
    intent_tags: list[str] = []
    volume_estimate: int | None = None       # None -> estimated deterministically


class PromptSuggestion(AppModel):
    text: str
    funnel_stage: FunnelStage = FunnelStage.TOFU
    intent_tags: list[str] = []
    volume_estimate: int = 0


class PromptResearchRequest(AppModel):
    topic: str
    limit: int = Field(default=20, ge=1, le=100)


class PromptResearchResult(AppModel):
    topic: str
    suggestions: list[PromptSuggestion] = []
    total: int = 0


class PromptRankPoint(AppModel):
    day: date
    rank: int | None = None  # None = brand absent from the engine's ranked list


class PromptEngineRank(AppModel):
    engine: AnswerEngine
    current_rank: int | None = None
    previous_rank: int | None = None
    best_rank: int | None = None
    history: list[PromptRankPoint] = []

    @property
    def delta(self) -> int | None:
        if self.current_rank is None or self.previous_rank is None:
            return None
        # Positive delta = improvement (moved closer to #1)
        return self.previous_rank - self.current_rank


class PromptTrackerEntry(AppModel):
    prompt: TrackedPrompt
    engines: list[PromptEngineRank] = []


class PromptTrackerReport(AppModel):
    brand: str
    total_prompts: int = 0
    engines: list[AnswerEngine] = []
    entries: list[PromptTrackerEntry] = []


# ---------------------------------------------------------------------------
# Citation & source mapping
# ---------------------------------------------------------------------------


class CitationScanRequest(AppModel):
    brand: str
    prompts: list[str] = []  # empty -> use the org's tracked prompt library
    engines: list[AnswerEngine] = []
    own_domain: str | None = None  # None -> derived from brand name


class EngineCitations(AppModel):
    engine: AnswerEngine
    citations: list[Citation] = []


class DomainStats(AppModel):
    """Aggregated citation stats + trust analysis for one source domain."""

    domain: str
    category: DomainCategory = DomainCategory.OTHER
    trust_weight: float = Field(default=0.0, ge=0.0, le=1.0)
    citations: int = 0
    frequency: float = 0.0  # share of all citations pointing at this domain
    engines: list[AnswerEngine] = []
    priority_score: float = 0.0  # trust_weight x frequency, 0-100


class CitationReport(AppModel):
    brand: str
    scanned_on: date
    total_citations: int = 0
    engines: list[EngineCitations] = []
    domains: list[DomainStats] = []  # sorted by priority_score desc


class DomainTrustReport(AppModel):
    """Org-wide aggregated view of every domain seen across citation scans."""

    total_citations: int = 0
    domains: list[DomainStats] = []


# ---------------------------------------------------------------------------
# Sentiment profiling
# ---------------------------------------------------------------------------


class SentimentScanRequest(AppModel):
    brand: str
    prompts: list[str] = []  # empty -> use the org's tracked prompt library
    engines: list[AnswerEngine] = []


class SentimentCell(AppModel):
    """One heatmap cell: sentiment of one engine's answer to one prompt."""

    engine: AnswerEngine
    prompt: str
    label: SentimentLabel = SentimentLabel.NEUTRAL
    score: float = Field(default=0.0, ge=-1.0, le=1.0)


class EngineSentiment(AppModel):
    engine: AnswerEngine
    avg_score: float = 0.0
    label: SentimentLabel = SentimentLabel.NEUTRAL


class SentimentReport(AppModel):
    brand: str
    scanned_on: date
    cells: list[SentimentCell] = []       # engine x prompt heatmap
    per_engine: list[EngineSentiment] = []
    overall_score: float = 0.0
    overall_label: SentimentLabel = SentimentLabel.NEUTRAL


# ---------------------------------------------------------------------------
# AI readiness audit
# ---------------------------------------------------------------------------


class SiteArtifacts(AppModel):
    """Raw site artifacts an AI-readiness audit inspects (fetched or injected)."""

    base_url: str
    llms_txt: str | None = None
    robots_txt: str | None = None
    html: str = ""


class ReadinessRequest(AppModel):
    url: str


class AiCrawlerAccess(AppModel):
    crawler: str
    allowed: bool = True


class ReadinessCheck(AppModel):
    code: str
    label: str
    passed: bool
    weight: int = 1
    message: str = ""


class ReadinessReport(AppModel):
    url: str
    score: int = 0  # 0-100 weighted
    grade: str = "F"
    passed_count: int = 0
    total_count: int = 0
    checks: list[ReadinessCheck] = []
    crawler_access: list[AiCrawlerAccess] = []
    fixes: list[Issue] = []  # prioritized: most severe first
