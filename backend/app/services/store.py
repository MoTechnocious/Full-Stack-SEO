"""Thread-safe in-memory store.

A deliberately small persistence seam: the API and engines depend on this
interface, so swapping in Postgres/Redis later only touches this file.
"""
from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoid import cycles at runtime
    from app.models.audit import CrawlResult
    from app.models.integrations import DeliveryLog, LeadRecord
    from app.models.keywords import RankTrackingSummary, TrackedKeyword
    from app.models.reporting import ActionPlan, Report


class InMemoryStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._crawls: dict[str, "CrawlResult"] = {}
        self._tracked: dict[str, list["TrackedKeyword"]] = {}       # key: domain|country
        self._summaries: dict[str, "RankTrackingSummary"] = {}
        self._plans: dict[str, "ActionPlan"] = {}
        self._reports: dict[str, "Report"] = {}
        self._leads: dict[str, "LeadRecord"] = {}
        self._deliveries: dict[str, "DeliveryLog"] = {}

    # ---- Crawls ----
    def save_crawl(self, crawl: "CrawlResult") -> "CrawlResult":
        with self._lock:
            self._crawls[crawl.crawl_id] = crawl
        return crawl

    def get_crawl(self, crawl_id: str) -> "CrawlResult | None":
        with self._lock:
            return self._crawls.get(crawl_id)

    def list_crawls(self) -> list["CrawlResult"]:
        with self._lock:
            return list(self._crawls.values())

    # ---- Rank tracking ----
    @staticmethod
    def rank_key(domain: str, country: str) -> str:
        return f"{domain.lower()}|{country.lower()}"

    def save_tracked(self, domain: str, country: str, keywords: list["TrackedKeyword"]) -> None:
        with self._lock:
            self._tracked[self.rank_key(domain, country)] = keywords

    def get_tracked(self, domain: str, country: str) -> list["TrackedKeyword"]:
        with self._lock:
            return list(self._tracked.get(self.rank_key(domain, country), []))

    def save_summary(self, summary: "RankTrackingSummary") -> None:
        with self._lock:
            self._summaries[self.rank_key(summary.domain, summary.country)] = summary

    def get_summary(self, domain: str, country: str) -> "RankTrackingSummary | None":
        with self._lock:
            return self._summaries.get(self.rank_key(domain, country))

    # ---- Plans / reports ----
    def save_plan(self, plan: "ActionPlan") -> None:
        with self._lock:
            self._plans[plan.site] = plan

    def get_plan(self, site: str) -> "ActionPlan | None":
        with self._lock:
            return self._plans.get(site)

    def save_report(self, report: "Report") -> None:
        with self._lock:
            self._reports[report.report_id] = report

    def get_report(self, report_id: str) -> "Report | None":
        with self._lock:
            return self._reports.get(report_id)

    # ---- Leads / deliveries ----
    def save_lead(self, lead: "LeadRecord") -> None:
        with self._lock:
            if lead.id:
                self._leads[lead.id] = lead

    def get_lead(self, lead_id: str) -> "LeadRecord | None":
        with self._lock:
            return self._leads.get(lead_id)

    def save_delivery(self, log: "DeliveryLog") -> None:
        with self._lock:
            self._deliveries[log.id] = log

    def list_deliveries(self) -> list["DeliveryLog"]:
        with self._lock:
            return list(self._deliveries.values())

    def clear(self) -> None:
        with self._lock:
            self._crawls.clear()
            self._tracked.clear()
            self._summaries.clear()
            self._plans.clear()
            self._reports.clear()
            self._leads.clear()
            self._deliveries.clear()


_STORE: InMemoryStore | None = None
_STORE_LOCK = threading.Lock()


def get_store() -> InMemoryStore:
    """Return the process-wide store singleton."""
    global _STORE
    if _STORE is None:
        with _STORE_LOCK:
            if _STORE is None:
                _STORE = InMemoryStore()
    return _STORE
