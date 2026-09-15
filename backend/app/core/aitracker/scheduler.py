"""Refresh scheduling helpers: which tracker configs are due at a given time.

Pure functions only — no threads, no cron. The actual trigger is pluggable by
design: Celery beat, APScheduler, or a k8s CronJob can call ``due_runs(now)``
(or poll the ``GET /ai-tracker/due`` ops endpoint) and dispatch
``run_tracker`` / ``POST /configs/{id}/run`` for every hit.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.aitracker.store import TrackerStore, get_tracker_store
from app.models.aitracker import RefreshCadence, TrackerConfig

CADENCE_INTERVALS: dict[RefreshCadence, timedelta] = {
    RefreshCadence.DAILY: timedelta(days=1),
    RefreshCadence.WEEKLY: timedelta(days=7),
}


def _as_utc(moment: datetime) -> datetime:
    """Treat naive datetimes as UTC so comparisons never raise."""
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment


def is_due(config: TrackerConfig, now: datetime) -> bool:
    """True when the config has never run, or its cadence interval has elapsed."""
    if config.last_run_at is None:
        return True
    interval = CADENCE_INTERVALS[config.refresh_cadence]
    return _as_utc(now) - _as_utc(config.last_run_at) >= interval


def due_runs(
    now: datetime | None = None,
    org_id: str | None = None,
    store: TrackerStore | None = None,
) -> list[tuple[str, TrackerConfig]]:
    """All ``(org_id, config)`` pairs due for refresh at ``now``.

    Pass ``org_id`` to restrict to one tenant (as the ops endpoint does);
    without it, every org is scanned — the shape a queue producer wants.
    """
    store = store or get_tracker_store()
    now = now or datetime.now(timezone.utc)
    org_ids = [org_id] if org_id is not None else store.org_ids()
    return [
        (org, config)
        for org in org_ids
        for config in store.list_configs(org)
        if is_due(config, now)
    ]
