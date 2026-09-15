"""Lead-gen audit widget routes — PUBLIC (no auth), embeddable on any site.

``GET /widget/audit.js`` serves a self-contained, org-branded embed script;
``POST /widget/leads`` validates and captures a lead (org-scoped via the widget
slug) and returns a deterministic mock mini-audit teaser. Follows the public
inbound pattern from :mod:`app.api.routes_integrations` — only the settings
dependency, never a tenant context.
"""
from __future__ import annotations

import hashlib
import re
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import get_settings_dep
from app.config import Settings
from app.integrations.crm_pipeline import LeadPipeline, get_crm_adapter
from app.integrations.make_gateway import MakeGateway
from app.models.common import AppModel, grade_from_score
from app.models.integrations import DeliveryStatus, LeadRecord
from app.services.store import InMemoryStore

router = APIRouter(prefix="/widget", tags=["widget"])

_SLUG_RE = re.compile(r"[^a-z0-9-]")

# Canned finding pool for the deterministic mock mini-audit teaser.
_FINDINGS_POOL: tuple[str, ...] = (
    "Your homepage title tag could be better optimized for your target keywords.",
    "Some pages appear to be missing meta descriptions, which hurts click-through rates.",
    "Improving image alt text would make your site more accessible and easier to rank.",
    "Your site could benefit from more internal links between related pages.",
    "Page speed optimizations could improve both rankings and user experience.",
    "Adding structured data would help search engines understand your content.",
)

# Self-contained embed snippet; __ORG__ is replaced with the sanitized org slug.
_WIDGET_JS_TEMPLATE = """(function () {
  "use strict";
  var ORG = "__ORG__";
  var ENDPOINT = "/widget/leads";
  var mount = document.getElementById("myseo-audit-widget");
  if (!mount) {
    mount = document.createElement("div");
    mount.id = "myseo-audit-widget";
    document.body.appendChild(mount);
  }
  mount.innerHTML =
    '<div style="max-width:360px;font-family:system-ui,sans-serif;border:1px solid #e5e7eb;' +
    'border-radius:12px;padding:20px;box-shadow:0 4px 12px rgba(0,0,0,.08)">' +
    '<h3 style="margin:0 0 4px;font-size:18px">Free SEO Audit</h3>' +
    '<p style="margin:0 0 12px;font-size:13px;color:#6b7280">Powered by ' + ORG + '</p>' +
    '<form id="myseo-audit-form">' +
    '<input name="url" required placeholder="Your website URL" style="width:100%;margin:0 0 8px;padding:8px;border:1px solid #d1d5db;border-radius:8px;box-sizing:border-box">' +
    '<input name="email" type="email" required placeholder="Your email" style="width:100%;margin:0 0 8px;padding:8px;border:1px solid #d1d5db;border-radius:8px;box-sizing:border-box">' +
    '<input name="name" placeholder="Your name (optional)" style="width:100%;margin:0 0 12px;padding:8px;border:1px solid #d1d5db;border-radius:8px;box-sizing:border-box">' +
    '<button type="submit" style="width:100%;padding:10px;border:0;border-radius:8px;background:#4f46e5;color:#fff;font-weight:600;cursor:pointer">Get my free audit</button>' +
    '</form><div id="myseo-audit-result" style="margin-top:12px;font-size:13px"></div></div>';
  var form = document.getElementById("myseo-audit-form");
  var result = document.getElementById("myseo-audit-result");
  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    var data = new FormData(form);
    result.textContent = "Running your audit\\u2026";
    fetch(ENDPOINT + "?org=" + encodeURIComponent(ORG), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: data.get("url"),
        email: data.get("email"),
        name: data.get("name") || null,
        org: ORG
      })
    })
      .then(function (res) { return res.json(); })
      .then(function (body) {
        if (body && body.teaser) {
          result.innerHTML =
            "<strong>Score: " + body.teaser.score + "/100 (" + body.teaser.grade + ")</strong><br>" +
            body.teaser.summary + "<ul>" +
            body.teaser.top_findings.map(function (f) { return "<li>" + f + "</li>"; }).join("") +
            "</ul>";
        } else {
          result.textContent = (body && body.errors && body.errors.join(", ")) ||
            "We could not run the audit. Please check your details and try again.";
        }
      })
      .catch(function () { result.textContent = "Something went wrong. Please try again."; });
  });
})();
"""


def _sanitize_slug(org: str) -> str:
    slug = _SLUG_RE.sub("", (org or "").strip().lower().replace(" ", "-"))[:40]
    return slug or "default"


def _domain_of(url: str) -> str:
    raw = (url or "").strip()
    if "://" not in raw:
        raw = f"https://{raw}"
    netloc = urlparse(raw).netloc.lower()
    return netloc or raw.lower()


class MiniAuditTeaser(AppModel):
    """Lightweight mock audit summary returned to the widget."""

    site: str
    score: int
    grade: str
    summary: str
    top_findings: list[str] = []


class WidgetLeadBody(AppModel):
    url: str
    email: str
    name: str | None = None
    org: str = "default"


class WidgetLeadResponse(AppModel):
    lead_id: str | None = None
    status: DeliveryStatus
    errors: list[str] = []
    teaser: MiniAuditTeaser | None = None


def run_mini_audit(url: str) -> MiniAuditTeaser:
    """Deterministic mock mini-audit: same URL always yields the same teaser."""
    domain = _domain_of(url)
    digest = hashlib.sha256(domain.encode("utf-8")).digest()
    score = 45 + digest[0] % 41  # 45-85: room to improve, never hopeless
    grade = grade_from_score(score)

    findings: list[str] = []
    for byte in digest:
        candidate = _FINDINGS_POOL[byte % len(_FINDINGS_POOL)]
        if candidate not in findings:
            findings.append(candidate)
        if len(findings) == 3:
            break

    summary = (
        f"{domain} scores {score}/100 ({grade}). We found several quick wins — "
        "a full audit report with step-by-step fixes is on its way to your inbox."
    )
    return MiniAuditTeaser(
        site=domain, score=score, grade=grade, summary=summary, top_findings=findings
    )


@router.get("/audit.js")
async def widget_script_route(org: str = Query("default", max_length=64)) -> Response:
    """Serve the embeddable audit-form snippet, branded with the org slug. PUBLIC."""
    slug = _sanitize_slug(org)
    return Response(
        content=_WIDGET_JS_TEMPLATE.replace("__ORG__", slug),
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.post("/leads", response_model=WidgetLeadResponse)
async def widget_lead_route(
    body: WidgetLeadBody,
    settings: Settings = Depends(get_settings_dep),
) -> WidgetLeadResponse:
    """Capture a widget lead (org-scoped via slug) and return an audit teaser. PUBLIC."""
    slug = _sanitize_slug(body.org)
    email = body.email.strip()
    # The widget only requires an email; default the name so validation can pass.
    name = (body.name or "").strip() or (email.split("@")[0] if "@" in email else "")
    lead = LeadRecord(
        name=name,
        email=email,
        website=body.url,
        source=f"widget:{slug}",
        custom_fields={"org_slug": slug},
    )

    gateway = MakeGateway(url=settings.make_webhook_url, secret=settings.make_signing_secret)
    pipeline = LeadPipeline(
        adapter=get_crm_adapter(settings), store=InMemoryStore(),
        make_gateway=gateway, max_retries=settings.integration_max_retries,
    )
    log = await pipeline.process(lead)

    if log.status == DeliveryStatus.REJECTED:
        errors = [e for e in (log.last_error or "invalid_lead").split("; ") if e]
        return WidgetLeadResponse(lead_id=log.lead_id, status=log.status, errors=errors)

    return WidgetLeadResponse(
        lead_id=log.lead_id, status=log.status, teaser=run_mini_audit(body.url)
    )
