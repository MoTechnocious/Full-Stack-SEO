"""Thread-safe, org-scoped in-memory repository for tracked PEO entities.

A deliberately small persistence seam (mirroring ``app.services.store``):
the PEO routes depend on this interface, so swapping in Postgres/Redis later
only touches this file.
"""
from __future__ import annotations

import threading

from app.models.peo import TrackedEntity


class PeoRepository:
    """Org-scoped storage for tracked Knowledge Graph entities."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._tracked: dict[str, dict[str, TrackedEntity]] = {}  # org_id -> kg_mid -> entity

    def track_entity(self, org_id: str, entity: TrackedEntity) -> TrackedEntity:
        with self._lock:
            self._tracked.setdefault(org_id, {})[entity.kg_mid] = entity
        return entity

    def get_tracked(self, org_id: str, kg_mid: str) -> TrackedEntity | None:
        with self._lock:
            return self._tracked.get(org_id, {}).get(kg_mid)

    def list_tracked(self, org_id: str) -> list[TrackedEntity]:
        with self._lock:
            return list(self._tracked.get(org_id, {}).values())

    def clear(self) -> None:
        with self._lock:
            self._tracked.clear()


_REPO: PeoRepository | None = None
_REPO_LOCK = threading.Lock()


def get_peo_repository() -> PeoRepository:
    """Return the process-wide PEO repository singleton."""
    global _REPO
    if _REPO is None:
        with _REPO_LOCK:
            if _REPO is None:
                _REPO = PeoRepository()
    return _REPO


def reset_peo_repository() -> None:
    """Clear all tracked state (used between tests)."""
    get_peo_repository().clear()
