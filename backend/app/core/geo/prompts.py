"""Prompt analytics & library: org-scoped tracked prompts, deterministic prompt
research (seed topic -> conversational queries), and the master prompt tracker
reporting brand rank per prompt per engine over time."""
from __future__ import annotations

import hashlib
from datetime import date

from app.core.geo.providers import AnswerEngineProvider, get_answer_engine_provider
from app.core.geo.store import GeoStore, get_geo_store
from app.core.geo.visibility import rank_in_list
from app.models.geo import (
    AnswerEngine,
    FunnelStage,
    PromptCreate,
    PromptEngineRank,
    PromptRankPoint,
    PromptResearchRequest,
    PromptResearchResult,
    PromptSuggestion,
    PromptTrackerEntry,
    PromptTrackerReport,
    TrackedPrompt,
)

# ---------------------------------------------------------------------------
# Funnel-stage / intent classification (deterministic heuristics)
# ---------------------------------------------------------------------------

_BOFU_MARKERS: tuple[str, ...] = (
    "pricing", "price", "cost", "discount", "buy", "trial", "demo", "coupon",
    "worth it", "sign up", "cheapest",
)
_MOFU_MARKERS: tuple[str, ...] = (
    "best", "top", "vs", "versus", "alternative", "compare", "comparison",
    "review", "which", "recommend",
)

_INTENT_TAGS: dict[FunnelStage, list[str]] = {
    FunnelStage.TOFU: ["discovery", "educational"],
    FunnelStage.MOFU: ["comparison", "evaluation"],
    FunnelStage.BOFU: ["purchase", "high-intent"],
}


def classify_funnel_stage(text: str) -> FunnelStage:
    """Heuristic funnel-stage classifier: BOFU markers > MOFU markers > TOFU."""
    lowered = text.lower()
    if any(marker in lowered for marker in _BOFU_MARKERS):
        return FunnelStage.BOFU
    if any(marker in lowered for marker in _MOFU_MARKERS):
        return FunnelStage.MOFU
    return FunnelStage.TOFU


def estimate_prompt_volume(text: str) -> int:
    """Stable monthly-volume estimate (50..9_999) derived from the prompt text via MD5."""
    digest = hashlib.md5(f"prompt-volume::{text.strip().lower()}".encode("utf-8")).hexdigest()
    return 50 + (int(digest, 16) % 9950)


def _prompt_id(org_id: str, text: str) -> str:
    """Stable short id for a prompt within an org."""
    digest = hashlib.md5(f"{org_id}::{text.strip().lower()}".encode("utf-8")).hexdigest()
    return f"prm_{digest[:12]}"


# ---------------------------------------------------------------------------
# Library CRUD
# ---------------------------------------------------------------------------


def add_prompt(
    org_id: str,
    body: PromptCreate,
    store: GeoStore | None = None,
    day: date | None = None,
) -> TrackedPrompt:
    """Add a prompt to the org's library (idempotent on normalized text).

    Missing ``funnel_stage`` / ``volume_estimate`` are filled deterministically;
    missing ``intent_tags`` default to the stage's canonical tags.
    """
    store = store or get_geo_store()
    existing = store.find_prompt_by_text(org_id, body.text)
    if existing is not None:
        return existing

    stage = body.funnel_stage or classify_funnel_stage(body.text)
    prompt = TrackedPrompt(
        id=_prompt_id(org_id, body.text),
        text=body.text.strip(),
        funnel_stage=stage,
        intent_tags=body.intent_tags or list(_INTENT_TAGS[stage]),
        volume_estimate=(
            body.volume_estimate
            if body.volume_estimate is not None
            else estimate_prompt_volume(body.text)
        ),
        created_on=day or date.today(),
    )
    store.save_prompt(org_id, prompt)
    return prompt


def list_prompts(org_id: str, store: GeoStore | None = None) -> list[TrackedPrompt]:
    """All tracked prompts for an org, in insertion order."""
    store = store or get_geo_store()
    return store.list_prompts(org_id)


# ---------------------------------------------------------------------------
# Prompt research (seed topic -> conversational queries)
# ---------------------------------------------------------------------------

_RESEARCH_TEMPLATES: tuple[str, ...] = (
    "what is the best {s} for small businesses",
    "which {s} do experts recommend",
    "what should I look for when choosing {s}",
    "how do I get started with {s}",
    "what are the top {s} tools in 2026",
    "is {s} worth paying for",
    "what is a good alternative to popular {s}",
    "how much does {s} cost per month",
    "compare the leading {s} options",
    "which {s} has the best reviews",
    "what {s} works best for beginners",
    "can you recommend a reliable {s}",
    "what are common mistakes when buying {s}",
    "which {s} offers the best free trial",
    "how does {s} improve results for teams",
    "what is the cheapest {s} that is still good",
    "which {s} is best for enterprise companies",
    "what questions should I ask a {s} vendor",
    "how do professionals evaluate {s}",
    "which {s} integrates with the most tools",
)


def research_prompts(req: PromptResearchRequest) -> PromptResearchResult:
    """Expand a seed topic into high-intent conversational queries.

    Deterministic: templates are filled in a fixed order and every suggestion's
    funnel stage / intent tags / volume estimate derive from the text alone.
    """
    topic = req.topic.strip()
    if not topic:
        return PromptResearchResult(topic=req.topic, suggestions=[], total=0)

    texts: list[str] = [t.format(s=topic) for t in _RESEARCH_TEMPLATES]
    extra = 1
    while len(texts) < req.limit:  # deterministic fallback beyond the template pool
        texts.append(f"what makes a {topic} option {extra} stand out")
        extra += 1

    suggestions: list[PromptSuggestion] = []
    for text in texts[: req.limit]:
        stage = classify_funnel_stage(text)
        suggestions.append(
            PromptSuggestion(
                text=text,
                funnel_stage=stage,
                intent_tags=list(_INTENT_TAGS[stage]),
                volume_estimate=estimate_prompt_volume(text),
            )
        )
    return PromptResearchResult(topic=topic, suggestions=suggestions, total=len(suggestions))


# ---------------------------------------------------------------------------
# Master prompt tracker
# ---------------------------------------------------------------------------


def build_prompt_tracker(
    org_id: str,
    brand: str,
    competitors: list[str] | None = None,
    engines: list[AnswerEngine] | None = None,
    provider: AnswerEngineProvider | None = None,
    store: GeoStore | None = None,
    day: date | None = None,
) -> PromptTrackerReport:
    """Poll every engine for every tracked prompt and roll rank history forward.

    Each call appends (or, for the same day, replaces) a
    :class:`PromptRankPoint` per (prompt, engine) and updates
    current/previous/best rank — mirroring
    :meth:`app.core.keywords.rank_tracker.RankTracker.record_positions`.
    """
    competitors = competitors or []
    engines = engines or list(AnswerEngine)
    provider = provider or get_answer_engine_provider()
    store = store or get_geo_store()
    day = day or date.today()

    entries: list[PromptTrackerEntry] = []
    for prompt in store.list_prompts(org_id):
        engine_ranks: list[PromptEngineRank] = []
        for engine in engines:
            answer = provider.ask(engine, prompt.text, brand, competitors)
            rank = rank_in_list(brand, answer.ranked_list)

            record = store.get_rank(org_id, brand, prompt.id, engine.value)
            if record is None:
                record = PromptEngineRank(engine=engine)

            if record.history and record.history[-1].day == day:
                record.history[-1] = PromptRankPoint(day=day, rank=rank)
            else:
                record.previous_rank = record.current_rank
                record.history.append(PromptRankPoint(day=day, rank=rank))
            record.current_rank = rank
            if rank is not None and (record.best_rank is None or rank < record.best_rank):
                record.best_rank = rank

            store.save_rank(org_id, brand, prompt.id, engine.value, record)
            engine_ranks.append(record)
        entries.append(PromptTrackerEntry(prompt=prompt, engines=engine_ranks))

    return PromptTrackerReport(
        brand=brand,
        total_prompts=len(entries),
        engines=engines,
        entries=entries,
    )
