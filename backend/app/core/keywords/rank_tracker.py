"""Rank tracking: persist tracked keywords, record daily positions, summarize visibility."""
from __future__ import annotations

from datetime import date

from app.core.keywords.providers import SerpProvider, get_serp_provider
from app.models.common import Device
from app.models.keywords import RankPoint, RankTrackingSummary, TrackedKeyword
from app.services.store import InMemoryStore, get_store
from app.utils.url import registrable_domain

# Approximate organic CTR-by-position curve (position 1 highest). Values
# beyond position 10 decay toward zero; anything past position 100 (or an
# unranked keyword) is 0.
_CTR_CURVE: dict[int, float] = {
    1: 0.28,
    2: 0.15,
    3: 0.11,
    4: 0.08,
    5: 0.07,
    6: 0.05,
    7: 0.04,
    8: 0.03,
    9: 0.02,
    10: 0.01,
}


def ctr_for_position(position: int | None) -> float:
    """Estimated organic click-through rate for a SERP position (0.0-1.0)."""
    if position is None or position < 1 or position > 100:
        return 0.0
    if position in _CTR_CURVE:
        return _CTR_CURVE[position]
    decay = _CTR_CURVE[10] * (10 / position) ** 2
    return round(max(0.0, decay), 4)


class RankTracker:
    """Tracks keyword rankings for a domain/country pair via an injectable SerpProvider."""

    def __init__(
        self, store: InMemoryStore | None = None, serp_provider: SerpProvider | None = None
    ) -> None:
        self.store = store or get_store()
        self.serp_provider = serp_provider or get_serp_provider()

    def add_keywords(
        self,
        domain: str,
        country: str,
        keywords: list[str],
        device: Device = Device.DESKTOP,
        search_volumes: dict[str, int] | None = None,
    ) -> None:
        """Register keywords for tracking. Existing entries keep their history."""
        search_volumes = search_volumes or {}
        by_keyword: dict[str, TrackedKeyword] = {
            tk.keyword: tk for tk in self.store.get_tracked(domain, country)
        }
        for kw in keywords:
            if kw in by_keyword:
                if kw in search_volumes:
                    by_keyword[kw].search_volume = search_volumes[kw]
                continue
            by_keyword[kw] = TrackedKeyword(
                keyword=kw,
                domain=domain,
                country=country,
                device=device,
                search_volume=search_volumes.get(kw, 0),
            )
        self.store.save_tracked(domain, country, list(by_keyword.values()))

    def record_positions(
        self,
        domain: str,
        country: str,
        positions: dict[str, tuple[int | None, str | None]],
        day: date | None = None,
    ) -> None:
        """Append a RankPoint per keyword and roll current/previous/best position forward."""
        day = day or date.today()
        tracked = self.store.get_tracked(domain, country)
        for tk in tracked:
            if tk.keyword not in positions:
                continue
            position, url = positions[tk.keyword]
            tk.previous_position = tk.current_position
            tk.current_position = position
            if position is not None and (tk.best_position is None or position < tk.best_position):
                tk.best_position = position
            tk.history.append(RankPoint(day=day, position=position, url=url))
        self.store.save_tracked(domain, country, tracked)

    def poll(self, domain: str, country: str, device: Device = Device.DESKTOP) -> None:
        """Fetch a live SERP for every tracked keyword and record the domain's position."""
        target = registrable_domain(domain)
        tracked = self.store.get_tracked(domain, country)
        positions: dict[str, tuple[int | None, str | None]] = {}
        for tk in tracked:
            analysis = self.serp_provider.fetch_serp(tk.keyword, country=country, device=device)
            match = next(
                (r for r in analysis.results if registrable_domain(r.domain or r.url) == target),
                None,
            )
            positions[tk.keyword] = (match.position, match.url) if match else (None, None)
        self.record_positions(domain, country, positions, day=date.today())

    def build_summary(self, domain: str, country: str) -> RankTrackingSummary:
        """Aggregate tracked keywords into a RankTrackingSummary and persist it in the store."""
        tracked = self.store.get_tracked(domain, country)
        ranked_positions = [tk.current_position for tk in tracked if tk.current_position is not None]

        avg_position = round(sum(ranked_positions) / len(ranked_positions), 2) if ranked_positions else 0.0
        top3 = sum(1 for p in ranked_positions if p <= 3)
        top10 = sum(1 for p in ranked_positions if p <= 10)

        improved = declined = unchanged = 0
        for tk in tracked:
            d = tk.delta
            if d is None:
                continue
            if d > 0:
                improved += 1
            elif d < 0:
                declined += 1
            else:
                unchanged += 1

        total_volume = sum(tk.search_volume for tk in tracked)
        if total_volume > 0:
            numerator = sum(ctr_for_position(tk.current_position) * tk.search_volume for tk in tracked)
            max_possible = ctr_for_position(1) * total_volume
            visibility_score = (
                round(min(100.0, max(0.0, (numerator / max_possible) * 100)), 2) if max_possible else 0.0
            )
        else:
            visibility_score = 0.0

        summary = RankTrackingSummary(
            domain=domain,
            country=country,
            total_keywords=len(tracked),
            avg_position=avg_position,
            improved=improved,
            declined=declined,
            unchanged=unchanged,
            top3=top3,
            top10=top10,
            visibility_score=visibility_score,
            keywords=tracked,
        )
        self.store.save_summary(summary)
        return summary
