"""Models for the Local SEO suite: GBP manager and citation/NAP distribution."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from app.models.common import AppModel


# ---------------------------------------------------------------------------
# Google Business Profile (GBP)
# ---------------------------------------------------------------------------


class GbpPostCreate(AppModel):
    """Payload for publishing a GBP post / update."""

    summary: str
    topic: str = "update"  # "update" | "offer" | "event"
    cta_url: str | None = None


class GbpPost(AppModel):
    id: str
    org_id: str
    summary: str
    topic: str = "update"
    cta_url: str | None = None
    state: str = "live"
    created_at: datetime


class GbpMetrics(AppModel):
    """GBP search performance metrics (views, searches, customer actions)."""

    org_id: str
    period_days: int = 30
    views_search: int = 0
    views_maps: int = 0
    searches_direct: int = 0
    searches_discovery: int = 0
    actions_website: int = 0
    actions_calls: int = 0
    actions_directions: int = 0


class ReviewSentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class GbpReview(AppModel):
    id: str
    author: str
    rating: int = Field(default=5, ge=1, le=5)
    text: str = ""
    created_at: datetime
    reply: str | None = None


class SuggestedReply(AppModel):
    """A generated reply suggestion for a review, keyed by rating/sentiment."""

    review_id: str
    sentiment: ReviewSentiment = ReviewSentiment.NEUTRAL
    text: str


# ---------------------------------------------------------------------------
# Citations / NAP distribution
# ---------------------------------------------------------------------------


class Directory(str, Enum):
    YELP = "yelp"
    APPLE_MAPS = "apple_maps"
    BING_PLACES = "bing_places"
    FOURSQUARE = "foursquare"


class NapRecord(AppModel):
    """Canonical org-scoped NAP (name/address/phone) record plus hours/site.

    When ``locked`` is true, drift found in a directory is both flagged and
    blocked: the sync engine re-pushes this canonical record over the drift.
    """

    name: str
    address: str
    phone: str
    website: str | None = None
    hours: dict[str, str] = Field(default_factory=dict)
    locked: bool = False


class NapDiff(AppModel):
    """One field-level difference between the canonical NAP and a listing."""

    field: str
    expected: str
    found: str


class ListingDeliveryState(str, Enum):
    IN_SYNC = "in_sync"
    CREATED = "created"
    UPDATED = "updated"
    FAILED = "failed"
    NOT_LISTED = "not_listed"
    DRIFT_FLAGGED = "drift_flagged"
    DRIFT_BLOCKED = "drift_blocked"


class DirectoryListing(AppModel):
    """The NAP data a directory currently holds for the business."""

    directory: Directory
    name: str = ""
    address: str = ""
    phone: str = ""
    website: str | None = None
    hours: dict[str, str] = Field(default_factory=dict)
    last_synced_at: datetime | None = None


class DirectorySyncResult(AppModel):
    directory: Directory
    state: ListingDeliveryState
    diffs: list[NapDiff] = []
    error: str | None = None


class CitationSyncReport(AppModel):
    """Per-directory delivery state for one sync pass."""

    org_id: str
    results: list[DirectorySyncResult] = []
    delivered: int = 0
    failed: int = 0


class DirectoryStatus(AppModel):
    directory: Directory
    listed: bool = False
    drift: bool = False
    diffs: list[NapDiff] = []
    state: ListingDeliveryState = ListingDeliveryState.IN_SYNC


class CitationStatusReport(AppModel):
    org_id: str
    locked: bool = False
    drift_detected: bool = False
    directories: list[DirectoryStatus] = []
