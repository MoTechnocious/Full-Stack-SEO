"""AEO SERP-question providers (People-Also-Ask + autocomplete).

Mirrors ``app.core.keywords.providers``: a fully deterministic ``Mock*``
provider used by default (and by every test) — hashlib-seeded, never
:mod:`random` — plus a documented live-integration skeleton that raises
``NotImplementedError`` until a real SERP client is wired in.
"""
from __future__ import annotations

import hashlib
import typing

from app.config import Settings, get_settings
from app.models.aeo import PAAQuestion

# --------------------------------------------------------------------------
# Protocol
# --------------------------------------------------------------------------


@typing.runtime_checkable
class SerpQuestionProvider(typing.Protocol):
    def paa_questions(
        self, seed: str, depth: int = 2, per_level: int = 4
    ) -> list[PAAQuestion]: ...

    def autocomplete(self, seed: str, limit: int = 10) -> list[str]: ...


# --------------------------------------------------------------------------
# Deterministic mock provider
# --------------------------------------------------------------------------


def _hash_int(value: str, salt: str = "") -> int:
    """Stable non-negative integer derived from ``value`` (+ ``salt``) via MD5."""
    digest = hashlib.md5(f"{salt}::{value}".strip().lower().encode("utf-8")).hexdigest()
    return int(digest, 16)


_ROOT_TEMPLATES: tuple[str, ...] = (
    "what is {s}",
    "how does {s} work",
    "why is {s} important",
    "is {s} worth it",
    "how much does {s} cost",
    "what are the benefits of {s}",
    "can beginners use {s}",
    "which {s} is best",
    "how do i get started with {s}",
    "what are common {s} mistakes",
)

# Follow-up chains: a clicked PAA question expands into narrower variants.
_FOLLOWUP_MODIFIERS: tuple[str, ...] = (
    "for beginners",
    "for small businesses",
    "in 2026",
    "compared to alternatives",
    "step by step",
    "without paid tools",
)

_AUTOCOMPLETE_SUFFIXES: tuple[str, ...] = (
    "meaning", "examples", "cost", "for beginners", "tools", "checklist",
    "strategy", "benefits", "vs seo", "near me", "template", "best practices",
    "certification", "salary", "course", "software", "agency", "trends",
    "statistics", "guide", "tips", "mistakes", "definition", "basics", "faq",
)


class MockSerpQuestionProvider:
    """Deterministic PAA + autocomplete generator. No network, no ``random``."""

    def paa_questions(
        self, seed: str, depth: int = 2, per_level: int = 4
    ) -> list[PAAQuestion]:
        """Root questions for ``seed`` plus follow-up chains up to ``depth``.

        Roots sit at depth 0 with ``parent=None``; each expansion level appends
        a deterministic modifier chosen by hashing the parent question, exactly
        like real PAA boxes narrow a clicked question.
        """
        seed = seed.strip()
        if not seed:
            return []

        seen: set[str] = set()
        questions: list[PAAQuestion] = []

        def _add(question: str, parent: str | None, level: int) -> PAAQuestion | None:
            key = question.lower()
            if key in seen:
                return None
            seen.add(key)
            paa = PAAQuestion(question=question, parent=parent, depth=level)
            questions.append(paa)
            return paa

        frontier = [
            q for q in (
                _add(template.format(s=seed), None, 0)
                for template in _ROOT_TEMPLATES[: max(1, per_level)]
            ) if q is not None
        ]

        for level in range(1, max(1, depth)):
            next_frontier: list[PAAQuestion] = []
            for parent in frontier:
                offset = _hash_int(parent.question, "paa-followup")
                for i in range(2):  # two follow-ups per expanded question
                    modifier = _FOLLOWUP_MODIFIERS[(offset + i) % len(_FOLLOWUP_MODIFIERS)]
                    child = _add(f"{parent.question} {modifier}", parent.question, level)
                    if child is not None:
                        next_frontier.append(child)
            frontier = next_frontier

        return questions

    def autocomplete(self, seed: str, limit: int = 10) -> list[str]:
        """Deterministic autocomplete pathway: seed + rotated suffix pool."""
        seed = seed.strip()
        if not seed:
            return []
        start = _hash_int(seed, "autocomplete") % len(_AUTOCOMPLETE_SUFFIXES)
        suggestions: list[str] = []
        for i in range(min(max(1, limit), len(_AUTOCOMPLETE_SUFFIXES))):
            suffix = _AUTOCOMPLETE_SUFFIXES[(start + i) % len(_AUTOCOMPLETE_SUFFIXES)]
            suggestions.append(f"{seed} {suffix}")
        return suggestions


# --------------------------------------------------------------------------
# Live skeleton
# --------------------------------------------------------------------------


class DataForSEOQuestionProvider:
    """Stub adapter for a live PAA/autocomplete SERP API (e.g. DataForSEO).

    Reads ``dataforseo_login`` / ``dataforseo_password`` from
    :class:`~app.config.Settings` but performs no HTTP calls; every call raises
    ``NotImplementedError`` until a real client is wired in.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        settings = settings or get_settings()
        self.login = getattr(settings, "dataforseo_login", None)
        self.password = getattr(settings, "dataforseo_password", None)

    def paa_questions(
        self, seed: str, depth: int = 2, per_level: int = 4
    ) -> list[PAAQuestion]:
        raise NotImplementedError("Configure SEO_DATAFORSEO_* to enable")

    def autocomplete(self, seed: str, limit: int = 10) -> list[str]:
        raise NotImplementedError("Configure SEO_DATAFORSEO_* to enable")


# --------------------------------------------------------------------------
# Factory
# --------------------------------------------------------------------------


def get_question_provider(settings: Settings | None = None) -> SerpQuestionProvider:
    settings = settings or get_settings()
    if getattr(settings, "serp_question_provider", "mock") == "mock":
        return MockSerpQuestionProvider()
    return DataForSEOQuestionProvider(settings=settings)
