"""Knowledge Graph sensor: volatility + trend analysis over confidence scores."""
from __future__ import annotations

import math

from app.models.peo import SensorObservation, SensorReport, TrendClass

# Classification thresholds (relative to the series' own scale, so a 900-point
# entity and a 90-point entity are judged by the same yardstick).
_VOLATILE_REL_STDDEV = 0.08   # stddev of deltas > 8% of the mean score -> volatile
_TREND_REL_CHANGE = 0.05      # |net change| > 5% of the first score -> rising/declining


def _stddev(values: list[float]) -> float:
    """Population standard deviation (0.0 for fewer than 2 values)."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


def classify_trend(scores: list[float]) -> TrendClass:
    """Classify a confidence-score series as rising/stable/volatile/declining.

    Volatility (stddev of consecutive deltas) is checked first: an erratic
    series is *volatile* even if it happens to end higher than it started.
    Otherwise the net change decides between rising, declining, and stable.
    """
    if len(scores) < 2:
        return TrendClass.STABLE
    deltas = [b - a for a, b in zip(scores, scores[1:])]
    mean = sum(scores) / len(scores)
    if mean > 0 and _stddev(deltas) / mean > _VOLATILE_REL_STDDEV:
        return TrendClass.VOLATILE
    first = scores[0]
    net = scores[-1] - first
    if first > 0:
        if net / first > _TREND_REL_CHANGE:
            return TrendClass.RISING
        if net / first < -_TREND_REL_CHANGE:
            return TrendClass.DECLINING
    return TrendClass.STABLE


def analyze_series(
    kg_mid: str, observations: list[SensorObservation], name: str = ""
) -> SensorReport:
    """Build a :class:`SensorReport` from a chronological observation series.

    ``volatility`` is the population stddev of consecutive score deltas —
    a direct measure of how erratically the Knowledge Graph's confidence in
    the entity moves between readings.
    """
    scores = [obs.score for obs in observations]
    deltas = [b - a for a, b in zip(scores, scores[1:])]
    return SensorReport(
        kg_mid=kg_mid,
        name=name,
        observations=observations,
        latest_score=scores[-1] if scores else 0.0,
        mean_score=round(sum(scores) / len(scores), 2) if scores else 0.0,
        net_change=round(scores[-1] - scores[0], 2) if len(scores) >= 2 else 0.0,
        volatility=round(_stddev(deltas), 2),
        trend=classify_trend(scores),
    )
