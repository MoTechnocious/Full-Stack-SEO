"""In-memory, org-scoped state for the AI tracker (configs + run history).

Mirrors :class:`app.core.geo.store.GeoStore`: every collection is keyed by
``org_id`` so tenants never see each other's configs or run history. The store
is process-local and can be swapped for a database-backed implementation later
without touching the engine or routes.
"""
from __future__ import annotations

from collections import defaultdict

from app.models.aitracker import TrackerConfig, TrackerRunReport


class TrackerStore:
    """Org-scoped container for tracker configs and their run history."""

    def __init__(self) -> None:
        # org_id -> config_id -> TrackerConfig (insertion-ordered)
        self._configs: dict[str, dict[str, TrackerConfig]] = defaultdict(dict)
        # org_id -> config_id -> [TrackerRunReport, ...] (chronological)
        self._runs: dict[str, dict[str, list[TrackerRunReport]]] = defaultdict(
            lambda: defaultdict(list)
        )
        # org_id -> monotonically increasing sequence (stable config ids)
        self._seq: dict[str, int] = defaultdict(int)

    # ---- Configs ----

    def list_configs(self, org_id: str) -> list[TrackerConfig]:
        return list(self._configs[org_id].values())

    def get_config(self, org_id: str, config_id: str) -> TrackerConfig | None:
        return self._configs[org_id].get(config_id)

    def save_config(self, org_id: str, config: TrackerConfig) -> None:
        self._configs[org_id][config.id] = config

    def delete_config(self, org_id: str, config_id: str) -> bool:
        existed = self._configs[org_id].pop(config_id, None) is not None
        self._runs[org_id].pop(config_id, None)
        return existed

    def find_config_by_name(self, org_id: str, name: str) -> TrackerConfig | None:
        needle = name.strip().lower()
        for config in self._configs[org_id].values():
            if config.name.strip().lower() == needle:
                return config
        return None

    def next_seq(self, org_id: str) -> int:
        self._seq[org_id] += 1
        return self._seq[org_id]

    def org_ids(self) -> list[str]:
        return [org_id for org_id, configs in self._configs.items() if configs]

    # ---- Run history ----

    def runs(self, org_id: str, config_id: str) -> list[TrackerRunReport]:
        return list(self._runs[org_id][config_id])

    def append_run(self, org_id: str, report: TrackerRunReport) -> None:
        self._runs[org_id][report.config_id].append(report)

    # ---- Lifecycle ----

    def reset(self) -> None:
        """Drop all state for every org (test isolation helper)."""
        self._configs.clear()
        self._runs.clear()
        self._seq.clear()


_store = TrackerStore()


def get_tracker_store() -> TrackerStore:
    """Return the process-wide TrackerStore singleton (overridable in tests)."""
    return _store


def reset_tracker_store() -> None:
    """Clear the singleton store — call between tests for isolation."""
    _store.reset()
