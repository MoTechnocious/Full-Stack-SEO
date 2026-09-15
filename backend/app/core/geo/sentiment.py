"""Lexicon-based sentiment profiling of engine answers about a brand.

Pure, offline NLP: a small polarity lexicon with negation flipping produces a
score in [-1, 1] per text, then an engine x prompt heatmap for the brand."""
from __future__ import annotations

from datetime import date

from app.core.geo.providers import AnswerEngineProvider, get_answer_engine_provider
from app.models.geo import (
    AnswerEngine,
    EngineSentiment,
    SentimentCell,
    SentimentLabel,
    SentimentReport,
)
from app.utils.text import tokenize

POSITIVE_WORDS: frozenset[str] = frozenset(
    """excellent outstanding great good reliable impressive love loved praise praised
    seamless intuitive best fast easy helpful robust trusted trustworthy powerful
    superior polished delightful affordable recommended win winning stellar""".split()
)

NEGATIVE_WORDS: frozenset[str] = frozenset(
    """poor bad disappointing unreliable frustrating buggy slow complaints complaint
    worst lags lagging expensive clunky confusing broken weak overpriced terrible
    awful mediocre outdated flawed fails failing""".split()
)

NEGATORS: frozenset[str] = frozenset({"not", "no", "never", "hardly", "barely", "isn't", "wasn't"})

# |score| must exceed this to leave the neutral band.
_NEUTRAL_BAND: float = 0.15


def score_sentiment(text: str) -> tuple[SentimentLabel, float]:
    """Score a text's polarity: ``(label, score)`` with score in [-1, 1].

    Counts lexicon hits, flipping polarity when the preceding token is a
    negator ("not reliable" counts as negative). The score is the normalized
    difference ``(pos - neg) / (pos + neg)``; texts inside the neutral band
    (or with no lexicon hits) are labelled neutral.
    """
    tokens = tokenize(text)
    positive = 0
    negative = 0
    for index, token in enumerate(tokens):
        negated = index > 0 and tokens[index - 1] in NEGATORS
        if token in POSITIVE_WORDS:
            negative += 1 if negated else 0
            positive += 0 if negated else 1
        elif token in NEGATIVE_WORDS:
            positive += 1 if negated else 0
            negative += 0 if negated else 1

    total = positive + negative
    if total == 0:
        return SentimentLabel.NEUTRAL, 0.0
    score = round((positive - negative) / total, 4)
    if score > _NEUTRAL_BAND:
        return SentimentLabel.POSITIVE, score
    if score < -_NEUTRAL_BAND:
        return SentimentLabel.NEGATIVE, score
    return SentimentLabel.NEUTRAL, score


def _label_for(score: float) -> SentimentLabel:
    if score > _NEUTRAL_BAND:
        return SentimentLabel.POSITIVE
    if score < -_NEUTRAL_BAND:
        return SentimentLabel.NEGATIVE
    return SentimentLabel.NEUTRAL


def scan_sentiment(
    brand: str,
    prompts: list[str],
    engines: list[AnswerEngine] | None = None,
    provider: AnswerEngineProvider | None = None,
    day: date | None = None,
) -> SentimentReport:
    """Build the engine x prompt sentiment heatmap for a brand.

    Each cell scores the full engine answer for that prompt; per-engine and
    overall aggregates are simple means of the cell scores.
    """
    engines = engines or list(AnswerEngine)
    provider = provider or get_answer_engine_provider()

    cells: list[SentimentCell] = []
    per_engine: list[EngineSentiment] = []
    for engine in engines:
        engine_scores: list[float] = []
        for prompt in prompts:
            answer = provider.ask(engine, prompt, brand, [])
            label, score = score_sentiment(answer.text)
            cells.append(SentimentCell(engine=engine, prompt=prompt, label=label, score=score))
            engine_scores.append(score)
        avg = round(sum(engine_scores) / len(engine_scores), 4) if engine_scores else 0.0
        per_engine.append(EngineSentiment(engine=engine, avg_score=avg, label=_label_for(avg)))

    overall = round(sum(c.score for c in cells) / len(cells), 4) if cells else 0.0
    return SentimentReport(
        brand=brand,
        scanned_on=day or date.today(),
        cells=cells,
        per_engine=per_engine,
        overall_score=overall,
        overall_label=_label_for(overall),
    )
