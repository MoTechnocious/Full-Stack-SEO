"""Cross-LLM brand visibility: mention frequency, share of voice, average
position in generated lists, and trend deltas versus the previous scan."""
from __future__ import annotations

from datetime import date

from app.core.geo.providers import AnswerEngineProvider, get_answer_engine_provider
from app.core.geo.store import GeoStore, get_geo_store
from app.models.geo import (
    AnswerEngine,
    EngineAnswer,
    EngineVisibility,
    VisibilityMetrics,
    VisibilityReport,
)
from app.utils.text import phrase_count


def rank_in_list(name: str, ranked_list: list[str]) -> int | None:
    """1-based position of ``name`` in a ranked list (case-insensitive), or None."""
    needle = name.strip().lower()
    for index, candidate in enumerate(ranked_list, start=1):
        if candidate.strip().lower() == needle:
            return index
    return None


def _metrics_from_answers(
    brand: str, competitors: list[str], answers: list[EngineAnswer]
) -> tuple[VisibilityMetrics, dict[str, int]]:
    """Aggregate one engine's (or all engines') answers into VisibilityMetrics.

    Returns the metrics plus raw competitor mention counts so callers can
    derive competitor share of voice without re-walking the answers.
    """
    prompts_scanned = len(answers)
    brand_mentions = 0
    positions: list[int] = []
    competitor_mentions: dict[str, int] = {c: 0 for c in competitors}

    for answer in answers:
        mentions = phrase_count(answer.text, brand)
        brand_mentions += mentions
        rank = rank_in_list(brand, answer.ranked_list)
        if rank is not None:
            positions.append(rank)
        for competitor in competitors:
            competitor_mentions[competitor] += phrase_count(answer.text, competitor)

    mentioned_in = sum(
        1
        for answer in answers
        if phrase_count(answer.text, brand) > 0 or rank_in_list(brand, answer.ranked_list)
    )
    total_voice = brand_mentions + sum(competitor_mentions.values())
    metrics = VisibilityMetrics(
        prompts_scanned=prompts_scanned,
        mentions=brand_mentions,
        mention_frequency=round(mentioned_in / prompts_scanned, 4) if prompts_scanned else 0.0,
        share_of_voice=round(brand_mentions / total_voice, 4) if total_voice else 0.0,
        avg_position=round(sum(positions) / len(positions), 2) if positions else None,
    )
    return metrics, competitor_mentions


def _apply_deltas(current: VisibilityMetrics, previous: VisibilityMetrics | None) -> None:
    """Fill trend-delta fields on ``current`` in place from a prior scan."""
    if previous is None:
        return
    current.mention_frequency_delta = round(
        current.mention_frequency - previous.mention_frequency, 4
    )
    current.share_of_voice_delta = round(current.share_of_voice - previous.share_of_voice, 4)
    if current.avg_position is not None and previous.avg_position is not None:
        # Positive delta = improvement (moved closer to #1).
        current.avg_position_delta = round(previous.avg_position - current.avg_position, 2)


def scan_visibility(
    org_id: str,
    brand: str,
    prompts: list[str],
    competitors: list[str] | None = None,
    engines: list[AnswerEngine] | None = None,
    provider: AnswerEngineProvider | None = None,
    store: GeoStore | None = None,
    day: date | None = None,
) -> VisibilityReport:
    """Query every engine for every prompt and aggregate brand visibility.

    Deterministic for a fixed provider. The finished report is appended to the
    org's scan history so the *next* scan for the same brand gets trend deltas
    (``*_delta`` fields) computed against this one.
    """
    competitors = competitors or []
    engines = engines or list(AnswerEngine)
    provider = provider or get_answer_engine_provider()
    store = store or get_geo_store()
    day = day or date.today()

    answers: list[EngineAnswer] = [
        provider.ask(engine, prompt, brand, competitors)
        for engine in engines
        for prompt in prompts
    ]

    previous_reports = store.visibility_history(org_id, brand)
    previous = previous_reports[-1] if previous_reports else None
    previous_by_engine: dict[AnswerEngine, VisibilityMetrics] = (
        {ev.engine: ev for ev in previous.engines} if previous else {}
    )

    engine_visibility: list[EngineVisibility] = []
    for engine in engines:
        engine_answers = [a for a in answers if a.engine == engine]
        metrics, _ = _metrics_from_answers(brand, competitors, engine_answers)
        ev = EngineVisibility(engine=engine, **metrics.model_dump())
        _apply_deltas(ev, previous_by_engine.get(engine))
        engine_visibility.append(ev)

    overall, competitor_mentions = _metrics_from_answers(brand, competitors, answers)
    _apply_deltas(overall, previous.overall if previous else None)

    total_voice = overall.mentions + sum(competitor_mentions.values())
    competitor_share = {
        name: (round(count / total_voice, 4) if total_voice else 0.0)
        for name, count in competitor_mentions.items()
    }

    report = VisibilityReport(
        brand=brand,
        competitors=competitors,
        scanned_on=day,
        engines=engine_visibility,
        overall=overall,
        competitor_share_of_voice=competitor_share,
        answers=answers,
    )
    store.append_visibility(org_id, report)
    return report
