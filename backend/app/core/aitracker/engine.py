"""The tracker run engine: executes a config's prompt matrix across engines,
parses every answer, and rolls results into deterministic metrics.

Formulas (all deterministic; rounding as noted):

* ``mention_rate``    = prompts where the brand appears (text or ranked list)
  / prompts asked (round 4).
* ``position_score``  = mean over all answers of ``1/rank`` (0 when absent),
  so rank 1 -> 1.0, rank 2 -> 0.5, absent -> 0 (round 4).
* ``citation_share``  = citations pointing at the brand's own domain / all
  citations (round 4; 0 when nothing was cited).
* **Visibility Score** (0-100) = round(100 * (0.5 * mention_rate
  + 0.3 * position_score + 0.2 * citation_share), 1).
* **Share-of-Voice**  = brand text mentions / (brand + competitor text
  mentions) (round 4), plus a per-competitor share dict.
* **Mention-Gap**     = per prompt: engines where >=1 competitor appears but
  the brand does not; ``opportunity_score`` = gap-engine count x distinct
  competitors mentioned (higher = bigger opportunity), ranked descending.
* Trend deltas        = current - previous run (``avg_position_delta`` is
  previous - current so positive means "moved closer to #1"); ``None`` on the
  first run.

Answers come from the GEO module's :class:`AnswerEngineProvider` (deterministic
mock by default). ``google_ai_mode`` — which geo's ``AnswerEngine`` enum lacks
— is queried through the ``google_ai_overviews`` front end with a deterministic
prompt suffix so its answers differ from AI Overviews without editing geo code.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.aitracker.store import TrackerStore, get_tracker_store
from app.core.geo.providers import AnswerEngineProvider, get_answer_engine_provider
from app.core.geo.sentiment import score_sentiment
from app.core.geo.visibility import rank_in_list
from app.models.aitracker import (
    EngineRollup,
    MentionGapEntry,
    MentionGapReport,
    RollupMetrics,
    TrackerAnswer,
    TrackerConfig,
    TrackerEngine,
    TrackerRunReport,
    VisibilityRollup,
)
from app.models.geo import AnswerEngine, SentimentLabel
from app.utils.text import phrase_count
from app.utils.url import registrable_domain

# Visibility Score blend weights (documented above; must sum to 1.0).
W_MENTION_RATE = 0.5
W_POSITION = 0.3
W_CITATION = 0.2

# Sentiment neutral band (same threshold the geo lexicon scorer uses).
_NEUTRAL_BAND = 0.15

# ``google_ai_mode`` is asked through the AI Overviews front end with this
# deterministic suffix, so the mock synthesizes distinct-but-stable answers.
_AI_MODE_SUFFIX = " via google ai mode"


def _sentiment_label(score: float) -> SentimentLabel:
    if score > _NEUTRAL_BAND:
        return SentimentLabel.POSITIVE
    if score < -_NEUTRAL_BAND:
        return SentimentLabel.NEGATIVE
    return SentimentLabel.NEUTRAL


def ask_engine(
    provider: AnswerEngineProvider,
    engine: TrackerEngine,
    prompt: str,
    brand: str,
    competitors: list[str],
):
    """Query one tracker engine through the GEO provider protocol."""
    if engine is TrackerEngine.GOOGLE_AI_MODE:
        return provider.ask(
            AnswerEngine.GOOGLE_AI_OVERVIEWS, prompt + _AI_MODE_SUFFIX, brand, competitors
        )
    return provider.ask(AnswerEngine(engine.value), prompt, brand, competitors)


def parse_answer(
    engine: TrackerEngine,
    prompt: str,
    raw,
    brand: str,
    competitors: list[str],
) -> TrackerAnswer:
    """Parse a raw engine answer for brand/competitor signals + sentiment."""
    mentions = phrase_count(raw.text, brand)
    position = rank_in_list(brand, raw.ranked_list)
    mentioned_competitors = sorted(
        {
            c
            for c in competitors
            if phrase_count(raw.text, c) > 0 or rank_in_list(c, raw.ranked_list) is not None
        }
    )
    label, score = score_sentiment(raw.text)
    return TrackerAnswer(
        engine=engine,
        prompt=prompt,
        text=raw.text,
        ranked_list=list(raw.ranked_list),
        citations=list(raw.citations),
        brand_mentioned=mentions > 0 or position is not None,
        brand_mentions=mentions,
        brand_position=position,
        competitors_mentioned=mentioned_competitors,
        sentiment_label=label,
        sentiment_score=score,
    )


def rollup_metrics(
    answers: list[TrackerAnswer], competitors: list[str], own_domain: str
) -> RollupMetrics:
    """Fold parsed answers (one engine's, or all) into :class:`RollupMetrics`."""
    total = len(answers)
    if total == 0:
        return RollupMetrics()

    mentioned = sum(1 for a in answers if a.brand_mentioned)
    positions = [a.brand_position for a in answers if a.brand_position is not None]
    mention_rate = round(mentioned / total, 4)
    avg_position = round(sum(positions) / len(positions), 2) if positions else None
    position_score = round(
        sum(1.0 / a.brand_position if a.brand_position else 0.0 for a in answers) / total, 4
    )

    total_citations = sum(len(a.citations) for a in answers)
    own_root = registrable_domain(own_domain)
    own_citations = sum(
        1
        for a in answers
        for c in a.citations
        if registrable_domain(c.domain or c.url) == own_root
    )
    citation_share = round(own_citations / total_citations, 4) if total_citations else 0.0

    visibility_score = round(
        100.0
        * (W_MENTION_RATE * mention_rate + W_POSITION * position_score + W_CITATION * citation_share),
        1,
    )

    brand_voice = sum(a.brand_mentions for a in answers)
    competitor_voice = {
        c: sum(phrase_count(a.text, c) for a in answers) for c in competitors
    }
    total_voice = brand_voice + sum(competitor_voice.values())
    share_of_voice = round(brand_voice / total_voice, 4) if total_voice else 0.0
    competitor_share = {
        c: (round(count / total_voice, 4) if total_voice else 0.0)
        for c, count in competitor_voice.items()
    }

    avg_sentiment = round(sum(a.sentiment_score for a in answers) / total, 4)

    return RollupMetrics(
        prompts_total=total,
        prompts_mentioned=mentioned,
        mention_rate=mention_rate,
        avg_position=avg_position,
        position_score=position_score,
        citation_share=citation_share,
        visibility_score=visibility_score,
        share_of_voice=share_of_voice,
        competitor_share_of_voice=competitor_share,
        avg_sentiment=avg_sentiment,
        sentiment_label=_sentiment_label(avg_sentiment),
    )


def _apply_deltas(current: RollupMetrics, previous: RollupMetrics | None) -> None:
    """Fill run-over-run trend deltas on ``current`` in place."""
    if previous is None:
        return
    current.visibility_score_delta = round(
        current.visibility_score - previous.visibility_score, 1
    )
    current.share_of_voice_delta = round(current.share_of_voice - previous.share_of_voice, 4)
    current.mention_rate_delta = round(current.mention_rate - previous.mention_rate, 4)
    if current.avg_position is not None and previous.avg_position is not None:
        # Positive delta = improvement (moved closer to #1).
        current.avg_position_delta = round(previous.avg_position - current.avg_position, 2)


def build_mention_gap(
    config: TrackerConfig, answers: list[TrackerAnswer], run_at: datetime
) -> MentionGapReport:
    """Prompts where competitors show up but the brand does not, ranked by
    opportunity (gap-engine count x distinct competitors mentioned)."""
    entries: list[MentionGapEntry] = []
    for prompt in config.prompts:
        gap_answers = [
            a
            for a in answers
            if a.prompt == prompt and not a.brand_mentioned and a.competitors_mentioned
        ]
        if not gap_answers:
            continue
        gap_engines = [a.engine for a in gap_answers]
        competitors_mentioned = sorted({c for a in gap_answers for c in a.competitors_mentioned})
        entries.append(
            MentionGapEntry(
                prompt=prompt,
                gap_engines=gap_engines,
                competitors_mentioned=competitors_mentioned,
                opportunity_score=float(len(gap_engines) * len(competitors_mentioned)),
            )
        )
    entries.sort(key=lambda e: (-e.opportunity_score, e.prompt))
    return MentionGapReport(
        config_id=config.id,
        brand=config.brand,
        run_at=run_at,
        total_prompts=len(config.prompts),
        entries=entries,
    )


def run_tracker(
    org_id: str,
    config: TrackerConfig,
    now: datetime | None = None,
    provider: AnswerEngineProvider | None = None,
    store: TrackerStore | None = None,
) -> TrackerRunReport:
    """Execute one scheduled/manual tracker run for ``config``.

    Deterministic for a fixed provider. The report is appended to the org's
    run history (so the *next* run gets trend deltas) and the config's
    ``last_run_at`` is advanced for the scheduler.
    """
    provider = provider or get_answer_engine_provider()
    store = store or get_tracker_store()
    run_at = now or datetime.now(timezone.utc)

    answers: list[TrackerAnswer] = [
        parse_answer(
            engine,
            prompt,
            ask_engine(provider, engine, prompt, config.brand, config.competitors),
            config.brand,
            config.competitors,
        )
        for engine in config.engines
        for prompt in config.prompts
    ]

    history = store.runs(org_id, config.id)
    previous = history[-1].rollup if history else None
    previous_by_engine: dict[TrackerEngine, RollupMetrics] = (
        {er.engine: er for er in previous.engines} if previous else {}
    )

    engine_rollups: list[EngineRollup] = []
    for engine in config.engines:
        metrics = rollup_metrics(
            [a for a in answers if a.engine == engine], config.competitors, config.own_domain
        )
        er = EngineRollup(engine=engine, **metrics.model_dump())
        _apply_deltas(er, previous_by_engine.get(engine))
        engine_rollups.append(er)

    overall = rollup_metrics(answers, config.competitors, config.own_domain)
    _apply_deltas(overall, previous.overall if previous else None)

    rollup = VisibilityRollup(
        config_id=config.id,
        brand=config.brand,
        run_at=run_at,
        engines=engine_rollups,
        overall=overall,
    )
    report = TrackerRunReport(
        config_id=config.id,
        brand=config.brand,
        run_at=run_at,
        engines=list(config.engines),
        answers=answers,
        rollup=rollup,
        mention_gap=build_mention_gap(config, answers, run_at),
    )
    store.append_run(org_id, report)
    config.last_run_at = run_at
    store.save_config(org_id, config)
    return report
