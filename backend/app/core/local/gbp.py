"""Google Business Profile manager.

``GbpProvider`` is the structural interface a real GBP API client would satisfy;
``MockGbpProvider`` is the deterministic in-memory default (seeded reviews, hash-
derived metrics — same org always yields the same numbers). The suggested-reply
generator is a pure function of rating + text sentiment. No network calls.
"""
from __future__ import annotations

import hashlib
import threading
import typing
from datetime import datetime, timezone

from app.models.local import (
    GbpMetrics,
    GbpPost,
    GbpPostCreate,
    GbpReview,
    ReviewSentiment,
    SuggestedReply,
)

# Naive negative-signal lexicon used to downgrade middling reviews to negative.
_NEGATIVE_WORDS: frozenset[str] = frozenset(
    """bad terrible awful horrible rude slow wait late dirty broken problem issue
    poor disappointed disappointing never worst refund scam unresolved""".split()
)

# Deterministic seed reviews created per org on first access (fixed ids/dates).
_SEED_REVIEWS: tuple[tuple[str, int, str], ...] = (
    ("Alice M.", 5, "Fantastic service, the team was quick and friendly!"),
    ("Ben K.", 3, "Decent experience overall, nothing special though."),
    ("Cara D.", 1, "Terrible communication, my problem was never resolved."),
)


class GbpProvider(typing.Protocol):
    """Structural interface every GBP provider (mock or real) must satisfy."""

    def publish_post(self, org_id: str, post: GbpPostCreate) -> GbpPost:
        """Publish a post/update to the org's business profile."""
        ...

    def fetch_metrics(self, org_id: str, period_days: int = 30) -> GbpMetrics:
        """Fetch search metrics (views, searches, customer actions)."""
        ...

    def list_reviews(self, org_id: str) -> list[GbpReview]:
        """List the org's reviews, newest first."""
        ...

    def reply_to_review(self, org_id: str, review_id: str, text: str) -> GbpReview | None:
        """Attach a reply to a review; returns None when the review is unknown."""
        ...


class MockGbpProvider(GbpProvider):
    """Deterministic in-memory GBP provider. Default for tests/dev."""

    provider = "mock"

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._posts: dict[str, list[GbpPost]] = {}
        self._reviews: dict[str, dict[str, GbpReview]] = {}
        self._post_counters: dict[str, int] = {}

    def _seed_reviews(self, org_id: str) -> dict[str, GbpReview]:
        reviews: dict[str, GbpReview] = {}
        for i, (author, rating, text) in enumerate(_SEED_REVIEWS, start=1):
            review = GbpReview(
                id=f"rev_{i:03d}",
                author=author,
                rating=rating,
                text=text,
                created_at=datetime(2026, 1, 10 + i, 12, 0, tzinfo=timezone.utc),
            )
            reviews[review.id] = review
        return reviews

    def publish_post(self, org_id: str, post: GbpPostCreate) -> GbpPost:
        with self._lock:
            count = self._post_counters.get(org_id, 0) + 1
            self._post_counters[org_id] = count
            created = GbpPost(
                id=f"gbp_{count:06d}",
                org_id=org_id,
                summary=post.summary,
                topic=post.topic,
                cta_url=post.cta_url,
                state="live",
                created_at=datetime.now(timezone.utc),
            )
            self._posts.setdefault(org_id, []).append(created)
            return created

    def list_posts(self, org_id: str) -> list[GbpPost]:
        with self._lock:
            return list(self._posts.get(org_id, []))

    def fetch_metrics(self, org_id: str, period_days: int = 30) -> GbpMetrics:
        digest = hashlib.sha256(f"gbp|{org_id}|{period_days}".encode("utf-8")).digest()
        return GbpMetrics(
            org_id=org_id,
            period_days=period_days,
            views_search=400 + digest[0] * 7,
            views_maps=200 + digest[1] * 5,
            searches_direct=100 + digest[2] * 3,
            searches_discovery=150 + digest[3] * 4,
            actions_website=30 + digest[4],
            actions_calls=10 + digest[5] % 90,
            actions_directions=20 + digest[6] % 120,
        )

    def list_reviews(self, org_id: str) -> list[GbpReview]:
        with self._lock:
            if org_id not in self._reviews:
                self._reviews[org_id] = self._seed_reviews(org_id)
            reviews = list(self._reviews[org_id].values())
        reviews.sort(key=lambda r: r.created_at, reverse=True)
        return reviews

    def reply_to_review(self, org_id: str, review_id: str, text: str) -> GbpReview | None:
        with self._lock:
            if org_id not in self._reviews:
                self._reviews[org_id] = self._seed_reviews(org_id)
            review = self._reviews[org_id].get(review_id)
            if review is None:
                return None
            review.reply = text
            return review


def classify_review_sentiment(review: GbpReview) -> ReviewSentiment:
    """Rating-first sentiment: >=4 positive, <=2 negative; 3-star reviews are
    neutral unless the text contains negative-signal words."""
    if review.rating >= 4:
        return ReviewSentiment.POSITIVE
    if review.rating <= 2:
        return ReviewSentiment.NEGATIVE
    words = {w.strip(".,!?").lower() for w in review.text.split()}
    if words & _NEGATIVE_WORDS:
        return ReviewSentiment.NEGATIVE
    return ReviewSentiment.NEUTRAL


def suggest_review_reply(review: GbpReview, business_name: str = "our team") -> SuggestedReply:
    """Generate a deterministic, on-tone reply suggestion for a review."""
    sentiment = classify_review_sentiment(review)
    first_name = review.author.split()[0] if review.author.strip() else "there"
    if sentiment == ReviewSentiment.POSITIVE:
        text = (
            f"Thank you so much, {first_name}! We're thrilled you had a great experience "
            f"with {business_name} — we look forward to seeing you again soon."
        )
    elif sentiment == ReviewSentiment.NEGATIVE:
        text = (
            f"We're truly sorry about your experience, {first_name}. This isn't the standard "
            f"{business_name} holds itself to — please contact us directly so we can make it right."
        )
    else:
        text = (
            f"Thanks for the honest feedback, {first_name}. We're always working to improve — "
            f"we'd love to hear what would earn that fifth star from {business_name}."
        )
    return SuggestedReply(review_id=review.id, sentiment=sentiment, text=text)


class GbpManager:
    """Thin org-facing facade over a :class:`GbpProvider` plus reply suggestions."""

    def __init__(self, provider: GbpProvider | None = None) -> None:
        self.provider = provider or get_gbp_provider()

    def publish_post(self, org_id: str, post: GbpPostCreate) -> GbpPost:
        return self.provider.publish_post(org_id, post)

    def metrics(self, org_id: str, period_days: int = 30) -> GbpMetrics:
        return self.provider.fetch_metrics(org_id, period_days)

    def reviews(self, org_id: str) -> list[GbpReview]:
        return self.provider.list_reviews(org_id)

    def suggested_replies(self, org_id: str, business_name: str = "our team") -> list[SuggestedReply]:
        return [
            suggest_review_reply(r, business_name)
            for r in self.provider.list_reviews(org_id)
            if r.reply is None
        ]

    def reply(self, org_id: str, review_id: str, text: str | None = None) -> GbpReview | None:
        """Reply to a review; falls back to the suggested reply when ``text`` is empty."""
        if not (text or "").strip():
            reviews = {r.id: r for r in self.provider.list_reviews(org_id)}
            review = reviews.get(review_id)
            if review is None:
                return None
            text = suggest_review_reply(review).text
        return self.provider.reply_to_review(org_id, review_id, typing.cast(str, text))


_PROVIDER: MockGbpProvider | None = None
_PROVIDER_LOCK = threading.Lock()


def get_gbp_provider() -> GbpProvider:
    """Return the process-wide mock GBP provider singleton."""
    global _PROVIDER
    if _PROVIDER is None:
        with _PROVIDER_LOCK:
            if _PROVIDER is None:
                _PROVIDER = MockGbpProvider()
    return _PROVIDER


def reset_gbp_provider() -> None:
    """Drop the singleton (test isolation)."""
    global _PROVIDER
    with _PROVIDER_LOCK:
        _PROVIDER = None
