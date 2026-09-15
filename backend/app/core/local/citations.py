"""Citation distributor: org-scoped NAP records synced across directories.

``DirectoryAdapter`` is the structural interface a real directory API client
(Yelp, Apple Maps, Bing Places, Foursquare) would satisfy; ``MockDirectoryAdapter``
is the deterministic in-memory default. ``CitationSyncEngine`` diffs the canonical
NAP against each directory listing, pushes updates, reports per-directory delivery
state, and — when the NAP is ``locked`` — blocks drift by re-pushing the canonical
record over any divergence. No network calls.
"""
from __future__ import annotations

import threading
import typing
from datetime import datetime, timezone

from app.models.local import (
    CitationStatusReport,
    CitationSyncReport,
    Directory,
    DirectoryListing,
    DirectoryStatus,
    DirectorySyncResult,
    ListingDeliveryState,
    NapDiff,
    NapRecord,
)

# NAP fields compared during drift detection (hours handled separately).
_NAP_FIELDS: tuple[str, ...] = ("name", "address", "phone", "website")


class DirectoryAdapter(typing.Protocol):
    """Structural interface every directory adapter (mock or real) must satisfy."""

    directory: Directory

    def fetch(self, org_id: str) -> DirectoryListing | None:
        """Return the org's current listing on this directory, or None if unlisted."""
        ...

    def push(self, org_id: str, nap: NapRecord) -> DirectoryListing:
        """Create/overwrite the org's listing with the canonical NAP.

        May raise on failure — the sync engine records failures per directory.
        """
        ...


class MockDirectoryAdapter(DirectoryAdapter):
    """Deterministic in-memory directory adapter. Default for tests/dev."""

    provider = "mock"

    def __init__(self, directory: Directory) -> None:
        self.directory = directory
        self._lock = threading.RLock()
        self._listings: dict[str, DirectoryListing] = {}

    def fetch(self, org_id: str) -> DirectoryListing | None:
        with self._lock:
            listing = self._listings.get(org_id)
            return listing.model_copy(deep=True) if listing else None

    def push(self, org_id: str, nap: NapRecord) -> DirectoryListing:
        listing = DirectoryListing(
            directory=self.directory,
            name=nap.name,
            address=nap.address,
            phone=nap.phone,
            website=nap.website,
            hours=dict(nap.hours),
            last_synced_at=datetime.now(timezone.utc),
        )
        with self._lock:
            self._listings[org_id] = listing
        return listing.model_copy(deep=True)

    def seed(self, org_id: str, listing: DirectoryListing) -> None:
        """Directly place a listing (used by tests to simulate drift)."""
        with self._lock:
            self._listings[org_id] = listing.model_copy(deep=True)


def diff_listing(nap: NapRecord, listing: DirectoryListing) -> list[NapDiff]:
    """Field-level differences between the canonical NAP and a directory listing."""
    diffs: list[NapDiff] = []
    for field in _NAP_FIELDS:
        expected = getattr(nap, field) or ""
        found = getattr(listing, field) or ""
        if expected != found:
            diffs.append(NapDiff(field=field, expected=str(expected), found=str(found)))
    if dict(nap.hours) != dict(listing.hours):
        diffs.append(
            NapDiff(
                field="hours",
                expected="; ".join(f"{d}: {h}" for d, h in sorted(nap.hours.items())),
                found="; ".join(f"{d}: {h}" for d, h in sorted(listing.hours.items())),
            )
        )
    return diffs


class CitationSyncEngine:
    """Org-scoped NAP registry + sync/drift engine over a set of directory adapters."""

    def __init__(self, adapters: typing.Sequence[DirectoryAdapter]) -> None:
        self.adapters: list[DirectoryAdapter] = list(adapters)
        self._lock = threading.RLock()
        self._naps: dict[str, NapRecord] = {}

    # ---- NAP registry ----
    def set_nap(self, org_id: str, nap: NapRecord) -> NapRecord:
        with self._lock:
            self._naps[org_id] = nap.model_copy(deep=True)
        return nap

    def get_nap(self, org_id: str) -> NapRecord | None:
        with self._lock:
            nap = self._naps.get(org_id)
            return nap.model_copy(deep=True) if nap else None

    # ---- Sync ----
    def sync(self, org_id: str, only: Directory | None = None) -> CitationSyncReport:
        """Diff the canonical NAP against every directory and push updates.

        Per-directory delivery states: ``created`` (was unlisted), ``updated``
        (drift corrected, diffs listed), ``in_sync`` (nothing to do), ``failed``
        (adapter raised). Raises :class:`KeyError` when no NAP is configured.
        """
        nap = self.get_nap(org_id)
        if nap is None:
            raise KeyError(f"No NAP record configured for org '{org_id}'.")

        results: list[DirectorySyncResult] = []
        for adapter in self.adapters:
            if only is not None and adapter.directory != only:
                continue
            try:
                listing = adapter.fetch(org_id)
                if listing is None:
                    adapter.push(org_id, nap)
                    results.append(
                        DirectorySyncResult(
                            directory=adapter.directory, state=ListingDeliveryState.CREATED
                        )
                    )
                    continue
                diffs = diff_listing(nap, listing)
                if diffs:
                    adapter.push(org_id, nap)
                    results.append(
                        DirectorySyncResult(
                            directory=adapter.directory,
                            state=ListingDeliveryState.UPDATED,
                            diffs=diffs,
                        )
                    )
                else:
                    results.append(
                        DirectorySyncResult(
                            directory=adapter.directory, state=ListingDeliveryState.IN_SYNC
                        )
                    )
            except Exception as exc:  # noqa: BLE001 - adapter failures are reported, not raised
                results.append(
                    DirectorySyncResult(
                        directory=adapter.directory,
                        state=ListingDeliveryState.FAILED,
                        error=str(exc),
                    )
                )

        delivered = sum(1 for r in results if r.state != ListingDeliveryState.FAILED)
        failed = sum(1 for r in results if r.state == ListingDeliveryState.FAILED)
        return CitationSyncReport(org_id=org_id, results=results, delivered=delivered, failed=failed)

    # ---- Drift status ----
    def status(self, org_id: str) -> CitationStatusReport:
        """Report per-directory drift against the canonical NAP.

        Unlocked NAP: drift is flagged (``drift_flagged``) but left untouched.
        Locked NAP: drift is flagged AND blocked — the canonical record is
        re-pushed over the divergent listing (``drift_blocked``).
        Raises :class:`KeyError` when no NAP is configured.
        """
        nap = self.get_nap(org_id)
        if nap is None:
            raise KeyError(f"No NAP record configured for org '{org_id}'.")

        statuses: list[DirectoryStatus] = []
        for adapter in self.adapters:
            try:
                listing = adapter.fetch(org_id)
            except Exception:  # noqa: BLE001 - unreachable directory -> treated as unlisted
                listing = None
            if listing is None:
                statuses.append(
                    DirectoryStatus(
                        directory=adapter.directory,
                        listed=False,
                        drift=False,
                        state=ListingDeliveryState.NOT_LISTED,
                    )
                )
                continue
            diffs = diff_listing(nap, listing)
            if not diffs:
                statuses.append(
                    DirectoryStatus(
                        directory=adapter.directory,
                        listed=True,
                        drift=False,
                        state=ListingDeliveryState.IN_SYNC,
                    )
                )
                continue
            state = ListingDeliveryState.DRIFT_FLAGGED
            if nap.locked:
                try:
                    adapter.push(org_id, nap)
                    state = ListingDeliveryState.DRIFT_BLOCKED
                except Exception:  # noqa: BLE001 - block attempt failed; drift stays flagged
                    state = ListingDeliveryState.FAILED
            statuses.append(
                DirectoryStatus(
                    directory=adapter.directory,
                    listed=True,
                    drift=True,
                    diffs=diffs,
                    state=state,
                )
            )

        return CitationStatusReport(
            org_id=org_id,
            locked=nap.locked,
            drift_detected=any(s.drift for s in statuses),
            directories=statuses,
        )


def build_mock_adapters() -> list[MockDirectoryAdapter]:
    """One deterministic mock adapter per supported directory."""
    return [MockDirectoryAdapter(directory) for directory in Directory]


_ENGINE: CitationSyncEngine | None = None
_ENGINE_LOCK = threading.Lock()


def get_citation_engine() -> CitationSyncEngine:
    """Return the process-wide citation engine singleton (mock adapters)."""
    global _ENGINE
    if _ENGINE is None:
        with _ENGINE_LOCK:
            if _ENGINE is None:
                _ENGINE = CitationSyncEngine(build_mock_adapters())
    return _ENGINE


def reset_citation_engine() -> None:
    """Drop the singleton (test isolation)."""
    global _ENGINE
    with _ENGINE_LOCK:
        _ENGINE = None
