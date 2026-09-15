"""On-page + content routes — tenant-scoped, quota on content scoring."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.billing.deps import require_quota
from app.billing.usage import UsageService
from app.core.onpage.analyzer import analyze_onpage
from app.core.onpage.content_score import score_content
from app.core.onpage.schema_generator import generate_schema
from app.db.session import get_session
from app.models.common import AppModel
from app.models.onpage import (
    ContentEditorRequest,
    ContentScore,
    OnPageRequest,
    OnPageResult,
    SchemaRequest,
    SchemaResult,
)
from app.tenancy.context import TenantContext
from app.tenancy.deps import require_permission

router = APIRouter(prefix="/onpage", tags=["onpage"])


@router.post("/analyze", response_model=OnPageResult)
async def analyze_route(
    req: OnPageRequest,
    ctx: TenantContext = Depends(require_permission("seo:read")),
) -> OnPageResult:
    return analyze_onpage(req)


class ContentScoreBody(AppModel):
    target_keyword: str
    content: str = ""
    country: str = "us"
    secondary_keywords: list[str] = []
    competitor_word_counts: list[int] = []
    competitor_texts: list[str] = []


@router.post("/content-score", response_model=ContentScore, dependencies=[Depends(require_permission("seo:write"))])
async def content_score_route(
    body: ContentScoreBody,
    ctx: TenantContext = Depends(require_quota("content_scores_per_month")),
    session: Session = Depends(get_session),
) -> ContentScore:
    req = ContentEditorRequest(
        target_keyword=body.target_keyword,
        content=body.content,
        country=body.country,
        secondary_keywords=body.secondary_keywords,
        competitor_word_counts=body.competitor_word_counts,
    )
    result = score_content(req, competitor_texts=body.competitor_texts or None)
    UsageService(session).record(ctx.org_id, "content_scores_per_month", 1)
    return result


@router.post("/schema", response_model=SchemaResult)
async def schema_route(
    req: SchemaRequest,
    ctx: TenantContext = Depends(require_permission("seo:write")),
) -> SchemaResult:
    return generate_schema(req)
