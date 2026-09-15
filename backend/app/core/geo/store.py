"""In-memory, org-scoped state for the GEO module.

Every collection is a dict keyed by ``org_id`` so tenants never see each
other's prompts, scan history, tracker data, or citation aggregates. The store
is process-local (like :class:`app.services.store.InMemoryStore`) and can be
swapped for a database-backed implementation later without touching engines.
"""
from __future__ import annotations

from collections import defaultdict

from app.models.geo import (
    CitationReport,
    PromptEngineRank,
    TrackedPrompt,
    VisibilityReport,
)


class GeoStore:
    """Org-scoped container for all GEO state (prompts, scans, tracker history)."""

    def __init__(self) -> None:
        # org_id -> prompt_id -> TrackedPrompt (insertion-ordered)
        self._prompts: dict[str, dict[str, TrackedPrompt]] = defaultdict(dict)
        # org_id -> brand(lower) -> [VisibilityReport, ...] (chronological)
        self._visibility: dict[str, dict[str, list[VisibilityReport]]] = defaultdict(dict)
        # org_id -> (brand(lower), prompt_id, engine) -> PromptEngineRank
        self._tracker: dict[str, dict[tuple[str, str, str], PromptEngineRank]] = defaultdict(dict)
        # org_id -> [CitationReport, ...] (chronological)
        self._citations: dict[str, list[CitationReport]] = defaultdict(list)

    # ---- Prompt library ----

    def list_prompts(self, org_id: str) -> list[TrackedPrompt]:
        return list(self._prompts[org_id].values())

    def get_prompt(self, org_id: str, prompt_id: str) -> TrackedPrompt | None:
        return self._prompts[org_id].get(prompt_id)

    def save_prompt(self, org_id: str, prompt: TrackedPrompt) -> None:
        self._prompts[org_id][prompt.id] = prompt

    def find_prompt_by_text(self, org_id: str, text: str) -> TrackedPrompt | None:
        needle = text.strip().lower()
        for prompt in self._prompts[org_id].values():
            if prompt.text.strip().lower() == needle:
                return prompt
        return None

    # ---- Visibility scan history (trend deltas) ----

    def visibility_history(self, org_id: str, brand: str) -> list[VisibilityReport]:
        return self._visibility[org_id].get(brand.strip().lower(), [])

    def append_visibility(self, org_id: str, report: VisibilityReport) -> None:
        self._visibility[org_id].setdefault(report.brand.strip().lower(), []).append(report)

    # ---- Master prompt tracker ----

    def get_rank(
        self, org_id: str, brand: str, prompt_id: str, engine: str
    ) -> PromptEngineRank | None:
        return self._tracker[org_id].get((brand.strip().lower(), prompt_id, engine))

    def save_rank(
        self, org_id: str, brand: str, prompt_id: str, engine: str, rank: PromptEngineRank
    ) -> None:
        self._tracker[org_id][(brand.strip().lower(), prompt_id, engine)] = rank

    # ---- Citation scans ----

    def citation_reports(self, org_id: str) -> list[CitationReport]:
        return list(self._citations[org_id])

    def append_citations(self, org_id: str, report: CitationReport) -> None:
        self._citations[org_id].append(report)

    # ---- Lifecycle ----

    def reset(self) -> None:
        """Drop all state for every org (test isolation helper)."""
        self._prompts.clear()
        self._visibility.clear()
        self._tracker.clear()
        self._citations.clear()


_store = GeoStore()


def get_geo_store() -> GeoStore:
    """Return the process-wide GeoStore singleton (overridable in tests)."""
    return _store


def reset_geo_store() -> None:
    """Clear the singleton store — call between tests for isolation."""
    _store.reset()
