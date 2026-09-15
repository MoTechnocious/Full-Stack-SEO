"""Standalone readability reporting (Flesch Reading Ease + supporting stats)."""
from __future__ import annotations

from app.utils.text import flesch_reading_ease, sentence_count, word_count

_GRADE_BANDS: tuple[tuple[float, str], ...] = (
    (90.0, "very_easy"),
    (80.0, "easy"),
    (70.0, "fairly_easy"),
    (60.0, "standard"),
    (50.0, "fairly_difficult"),
    (30.0, "difficult"),
)


def _grade_label(flesch: float) -> str:
    for threshold, label in _GRADE_BANDS:
        if flesch >= threshold:
            return label
    return "very_difficult"


def readability_report(text: str) -> dict:
    """Return a small readability summary for ``text``.

    Keys: ``flesch`` (float 0-100), ``grade_label`` (str), ``avg_sentence_length``
    (float), ``word_count`` (int), ``sentence_count`` (int).
    """
    flesch = flesch_reading_ease(text)
    wc = word_count(text)
    sc = sentence_count(text)
    avg_sentence_length = round(wc / sc, 2) if sc else 0.0
    return {
        "flesch": flesch,
        "grade_label": _grade_label(flesch),
        "avg_sentence_length": avg_sentence_length,
        "word_count": wc,
        "sentence_count": sc,
    }
