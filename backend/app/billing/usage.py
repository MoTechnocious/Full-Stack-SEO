"""Usage metering + quota enforcement.

Monthly metrics use "YYYY-MM" period counters; absolute-resource limits (sites,
tracked keywords, seats) are checked live against real counts via ``check_resource``.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session, select

from app.billing.entitlements import get_limit, is_unlimited
from app.db.models_billing import UsageRecord
from app.middleware.errors import QuotaExceededError

MONTHLY_METRICS = {
    "crawls_per_month",
    "content_scores_per_month",
    "keyword_lookups_per_month",
    "reports_per_month",
}


def current_period() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


class UsageService:
    def __init__(self, session: Session):
        self.s = session

    def _period_for(self, metric: str) -> str:
        return current_period() if metric in MONTHLY_METRICS else "total"

    def _get_row(self, org_id: str, metric: str) -> UsageRecord | None:
        return self.s.exec(
            select(UsageRecord).where(
                UsageRecord.org_id == org_id,
                UsageRecord.metric == metric,
                UsageRecord.period == self._period_for(metric),
            )
        ).first()

    def get_count(self, org_id: str, metric: str) -> int:
        row = self._get_row(org_id, metric)
        return row.count if row else 0

    def record(self, org_id: str, metric: str, amount: int = 1) -> int:
        row = self._get_row(org_id, metric)
        if row is None:
            row = UsageRecord(
                org_id=org_id, metric=metric, period=self._period_for(metric), count=0
            )
        row.count += amount
        row.updated_at = datetime.now(timezone.utc)
        self.s.add(row)
        self.s.commit()
        self.s.refresh(row)
        return row.count

    def check(
        self, org_id: str, plan_code: str, metric: str, amount: int = 1
    ) -> tuple[bool, int, int]:
        """Return (allowed, used, limit). limit == -1 means unlimited."""
        limit = get_limit(plan_code, metric)
        used = self.get_count(org_id, metric)
        if is_unlimited(limit):
            return True, used, -1
        return (used + amount <= limit), used, limit

    def enforce(self, org_id: str, plan_code: str, metric: str, amount: int = 1) -> None:
        allowed, used, limit = self.check(org_id, plan_code, metric, amount)
        if not allowed:
            raise QuotaExceededError(
                f"Monthly quota reached for '{metric}': {used}/{limit} on the "
                f"'{plan_code}' plan. Upgrade or wait for the next cycle."
            )

    @staticmethod
    def check_resource(plan_code: str, metric: str, current_count: int, amount: int = 1) -> None:
        """Enforce an absolute-resource limit (sites/seats/tracked keywords)."""
        limit = get_limit(plan_code, metric)
        if is_unlimited(limit):
            return
        if current_count + amount > limit:
            raise QuotaExceededError(
                f"Plan limit reached for '{metric}': {current_count}/{limit} on the "
                f"'{plan_code}' plan. Upgrade to add more."
            )

    def summary(self, org_id: str, plan_code: str) -> dict[str, dict[str, int]]:
        """Usage-vs-limit for all monthly metrics (for the billing/usage page)."""
        out: dict[str, dict[str, int]] = {}
        for metric in sorted(MONTHLY_METRICS):
            used = self.get_count(org_id, metric)
            out[metric] = {"used": used, "limit": get_limit(plan_code, metric)}
        return out
