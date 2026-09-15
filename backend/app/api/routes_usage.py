"""Usage / quota routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.billing.entitlements import get_limit
from app.billing.usage import UsageService
from app.db.session import get_session
from app.tenancy.context import TenantContext
from app.tenancy.deps import get_tenant_context
from app.tenancy.repositories import get_repos

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("")
def usage(ctx: TenantContext = Depends(get_tenant_context), session: Session = Depends(get_session)):
    monthly = UsageService(session).summary(ctx.org_id, ctx.plan_code)
    repos = get_repos(session, ctx.org_id)
    resources = {
        "sites": {"used": repos.count_projects(), "limit": get_limit(ctx.plan_code, "sites")},
        "tracked_keywords": {
            "used": repos.count_tracked_keywords(),
            "limit": get_limit(ctx.plan_code, "tracked_keywords"),
        },
    }
    return {"plan_code": ctx.plan_code, "monthly": monthly, "resources": resources}
