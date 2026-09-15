# MySEOapp — Authentication, RBAC & Billing

*Companion documents: `MULTI_TENANCY.md` (tenancy model, data model, request-flow diagram), `../SYSTEM_STATE.md` (module inventory), `spec/PRODUCT_SPEC.md` (product requirements). This document defines who can call MySEOapp, what they're allowed to do once authenticated, and how a plan/quota governs what they can run.*

---

## Part 1 — Authentication & RBAC

### 1.1 Delegated identity, app-owned authorization

MySEOapp deliberately splits "who are you" from "what are you allowed to do":

- **Authentication is delegated** to a pluggable identity provider (`backend/app/idp/`). The backend never owns the general-purpose credential story (password resets, MFA, social login, SSO) — it verifies a token that some IdP issued and trusts the claims inside it.
- **Authorization (RBAC) is entirely app-owned** (`backend/app/tenancy/rbac.py`). No IdP claim is trusted for *permissions* — role is always read from MySEOapp's own `memberships` table, keyed by `(org_id, user_id)`. This means the same person can be an `owner` in their own workspace and a read-only `client` in an agency's workspace, which no external IdP's role model could represent on its own (see §3, the agency multi-client model).

This split is what lets the product run entirely locally (built-in `dev` provider, zero third-party dependencies) while remaining a drop-in fit for a real customer's existing IdP later — swapping providers never touches the RBAC/permission code.

### 1.2 Identity providers — dev vs. external

| | Built-in `dev` provider | External providers (`clerk`, `supabase`, `auth0`) |
|---|---|---|
| Token format | HS256 JWT, signed by MySEOapp itself | RS256 JWT, signed by the vendor |
| Verification | `jwt.decode()` with the shared secret `SEO_JWT_SECRET` | `jwt.PyJWKClient` fetches the signing key from the vendor's JWKS endpoint; verified against `SEO_IDP_ISSUER` / `SEO_IDP_AUDIENCE` |
| Credentials | Email + password, PBKDF2-SHA256 hashed (200,000 iterations, random salt) — `app/security/passwords.py` | Owned entirely by the vendor; MySEOapp never sees a password |
| Signup / login endpoints | `POST /auth/signup`, `POST /auth/login` (both reject with 400 if `SEO_IDP_PROVIDER != "dev"`) | Handled by the vendor's own hosted UI/SDK; MySEOapp only ever sees the resulting bearer token |
| Config | none required — this is the zero-dependency local/dev/test path | `SEO_IDP_PROVIDER=<name>`, `SEO_IDP_JWKS_URL`, optionally `SEO_IDP_ISSUER` / `SEO_IDP_AUDIENCE` |
| When to use | Local development, tests (all 89 backend tests run against this provider), self-hosted deployments that don't want a third-party auth dependency | Production deployments that want managed auth (MFA, SSO, social login, breach detection) without building it in-house |

Both paths converge on the same `IdentityClaims` shape (`subject`, `email`, `name`, `provider`, optional `org_id`/`role` hints) so the rest of the stack — JIT provisioning, org resolution, RBAC — never branches on which provider was used.

**Just-in-time (JIT) provisioning.** The first time a verified external identity is seen, `provision_from_claims()` (`app/tenancy/provisioning.py`) creates a local `User` row automatically (matched afterwards by `idp_subject` + `idp_provider`, falling back to email). There is no separate "import your users" step when adopting an external IdP — a user simply becomes known to MySEOapp the first time they present a valid token.

### 1.3 RBAC — roles

Roles are ordered by privilege; every dependency check is a simple rank comparison or set-membership check, resolved fresh from the `memberships` table on every request (never cached in the token beyond an informational hint):

| Role | Rank | Intended for |
|---|---|---|
| `owner` | 4 (highest) | The person/team that created the organization; full control including billing |
| `agency_admin` | 3 | Senior team members who manage members, API keys, and all SEO/reporting work, but not billing |
| `editor` | 2 | Day-to-day operators who run audits, write content scores, manage leads/reports |
| `client` | 1 (lowest) | Read-only stakeholders — e.g. an agency's own client, viewing their site's results |

### 1.4 RBAC — permission matrix

Permissions are plain strings, checked via `has_permission(role, "resource:action")`. `owner` implicitly holds every permission (`"*"`); every other role has an explicit, hand-maintained set in `app/tenancy/rbac.py`:

| Permission | `client` | `editor` | `agency_admin` | `owner` |
|---|:---:|:---:|:---:|:---:|
| `projects:read` | Yes | Yes | Yes | Yes |
| `projects:write` | — | — | Yes | Yes |
| `seo:read` | Yes | Yes | Yes | Yes |
| `seo:run` (crawls, rank tracking) | — | Yes | Yes | Yes |
| `seo:write` (content scores, schema, on-page) | — | Yes | Yes | Yes |
| `reports:read` | Yes | Yes | Yes | Yes |
| `reports:write` (build reports/action plans) | — | Yes | Yes | Yes |
| `leads:read` | Yes | Yes | Yes | Yes |
| `leads:write` | — | Yes | Yes | Yes |
| `members:manage` (invite/remove members) | — | — | Yes | Yes |
| `apikeys:manage` (create/revoke API keys) | — | — | Yes | Yes |
| `billing:manage` (checkout, portal) | — | — | — | Yes |

Two guard styles are available as FastAPI dependencies and are used interchangeably depending on the route: `require_permission("seo:run")` (exact permission) and `require_min_role("editor")` (rank threshold). A denied check always returns **403 `forbidden`**, never a silent empty result — see `test_rbac_denies_client_role` and `test_rbac_client_cannot_manage_keys` in the backend suite for the enforced behavior (a `client` role gets 403 on member/key management; an unauthenticated request gets 401, never 403).

### 1.5 API keys

Self-hosted, script/CI-friendly credentials that skip the user/session model entirely:

- Generated via `POST /api-keys` (requires `apikeys:manage`, i.e. `agency_admin` or `owner`). The full secret (`msk_<random>`, `SEO_API_KEY_PREFIX` configurable) is returned **exactly once**; only its SHA-256 hash, prefix, and last 4 characters are persisted (`app/security/api_keys.py`) — identical philosophy to password storage.
- Sent as `X-API-Key: <secret>` on any request; resolved to a `TenantContext` in one lookup (hash the presented key, find the matching non-revoked row, load its org). No password, no JWT, no JIT provisioning involved.
- Each key is bound to exactly **one organization and one fixed role** at creation time (`role` field on the key, defaulting to `editor`) — a key cannot switch orgs the way a user session can.
- Revocation is a soft flag (`revoked=True`, `DELETE /api-keys/{id}`) rather than a hard delete, so `last_used_at` and audit history survive revocation.
- This is the preferred credential for the MCP server (`MYSEOAPP_API_KEY` env var, sent as `X-API-Key`) and the intended mechanism for CI pipelines or other machine callers. The MCP server also accepts `MYSEOAPP_TOKEN` (a user's bearer token) when no API key is configured, and rewrites any 401/402/403 the backend returns into an actionable tool error naming the exact fix (`mcp-server/src/apiClient.ts`/`config.ts`).

---

## Part 2 — Billing

### 2.1 Plan catalog

Plans are defined in code (`backend/app/billing/plans.py`) — the single source of truth for price, limits, and features. The database only stores which `plan_code` an organization is on. `-1` means unlimited.

**Limits**

| Plan | Price /mo | Price /yr | Sites | Tracked keywords | Crawls /mo | Pages /crawl | Content scores /mo | Keyword lookups /mo | Reports /mo | Seats |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Free** | $0 | $0 | 1 | 25 | 5 | 100 | 10 | 50 | 2 | 1 |
| **Starter** | $29 | $290 | 3 | 200 | 30 | 1,000 | 100 | 500 | 20 | 3 |
| **Pro** | $79 | $790 | 10 | 1,000 | 150 | 10,000 | 500 | 2,500 | 100 | 10 |
| **Agency** | $199 | $1,990 | 50 | 5,000 | 1,000 | 50,000 | 2,500 | 10,000 | 1,000 | 25 |
| **Enterprise** | Custom | Custom | Unlimited | Unlimited | Unlimited | Unlimited | Unlimited | Unlimited | Unlimited | Unlimited |

**Features**

| Feature flag | Free | Starter | Pro | Agency | Enterprise |
|---|:---:|:---:|:---:|:---:|:---:|
| `api_access` | — | Yes | Yes | Yes | Yes |
| `content_ai` | — | Yes | Yes | Yes | Yes |
| `mcp_access` | — | — | Yes | Yes | Yes |
| `competitor_analysis` | — | — | Yes | Yes | Yes |
| `scheduled_crawls` | — | — | Yes | Yes | Yes |
| `white_label` | — | — | — | Yes | Yes |
| `priority_support` | — | — | — | Yes | Yes |

`GET /billing/plans` exposes this same catalog publicly (no auth) for pricing-page consumption, so the marketing site and the app can never drift from what's actually enforced server-side.

### 2.2 Quota enforcement & 402 semantics

Two distinct guards, both implemented as FastAPI dependencies in `app/billing/deps.py`, and both surfaced as **HTTP 402** so clients can reliably distinguish "you're not allowed to do this at all" (403) from "you're allowed, but you've hit a plan ceiling" (402):

| Error code | Status | Raised by | Meaning |
|---|---|---|---|
| `feature_not_available` | 402 | `require_feature(flag)` | The org's plan doesn't include this capability at all (e.g. `white_label` on Free) |
| `quota_exceeded` | 402 | `require_quota(metric)` / `UsageService.enforce()` | The org has used up this period's/plan's allowance |
| `forbidden` | 403 | `require_permission` / `require_min_role` | The *role* isn't allowed to call this route, regardless of plan |
| `not_authenticated` | 401 | `get_tenant_context` | No valid credential presented at all |

Example error envelopes (all errors share the `ErrorResponse` shape — `error`, `detail`, `request_id`):

```json
{
  "error": "quota_exceeded",
  "detail": "Monthly quota reached for 'crawls_per_month': 5/5 on the 'free' plan. Upgrade or wait for the next cycle.",
  "request_id": "b6f0b3d2-..."
}
```
```json
{
  "error": "feature_not_available",
  "detail": "'white_label' is not included in the 'free' plan. Upgrade to enable it.",
  "request_id": "b6f0b3d2-..."
}
```

**Two kinds of limits, enforced differently:**

- **Monthly counters** (`crawls_per_month`, `content_scores_per_month`, `keyword_lookups_per_month`, `reports_per_month`) — tracked as a `UsageRecord` row keyed on `(org_id, metric, "YYYY-MM")`. The route dependency `require_quota(metric)` calls `UsageService.enforce()` **before** the action runs; on success, the route explicitly calls `UsageService.record()` **after** the action completes. Quota is only consumed by actions that actually succeeded.
- **Absolute resources** (`tracked_keywords`, and in principle `sites`/`seats`) — no counter row at all; `UsageService.check_resource(plan_code, metric, current_count, amount)` compares a **live** count (e.g. `TenantRepos.count_tracked_keywords()`) against the plan limit at the moment of the request.

**What's metered today, concretely:**

| Action | Metric | Enforcement | Recording |
|---|---|---|---|
| `POST /audit/crawl` | `crawls_per_month` | `require_quota` (blocks before running) | `UsageService.record()` after the crawl finishes |
| `POST /onpage/content-score` | `content_scores_per_month` | `require_quota` | `UsageService.record()` after scoring |
| `POST /keywords/research` | `keyword_lookups_per_month` | `require_quota` | `UsageService.record()` after research |
| `POST /reports/build` | `reports_per_month` | `require_quota` | `UsageService.record()` after the report builds |
| `POST /rankings/track` (adding keywords) | `tracked_keywords` | `UsageService.check_resource()` against a live count | n/a — derived live, no counter |
| Crawl depth | `pages_per_crawl` | **Clamped, not blocked** — `run_crawl_route` silently caps `max_pages` to the plan's ceiling rather than rejecting the request | n/a |
| White-label branding on a report | `white_label` (feature) | `has_feature()` checked inline in `routes_reports.py`; falls back to default MySEOapp branding rather than erroring | n/a |
| Site / project count | `sites` | **Not yet enforced** — reported in `GET /usage` (`resources.sites`) but no project-creation route exists yet to gate | n/a |
| Team seats | `seats` | **Not yet enforced** — tracked on `Subscription.seats`; invite creation does not currently call `check_resource` | n/a |

`GET /usage` returns the used/limit pair for every monthly metric plus the two tracked resource metrics (`sites`, `tracked_keywords`) in one call — this is the endpoint the dashboard's usage/billing page reads.

### 2.3 Billing providers — mock vs. Stripe

`backend/app/billing/providers.py` defines a `BillingProvider` protocol (`create_checkout`, `create_portal`, `verify_webhook`) with two implementations, selected by `SEO_BILLING_PROVIDER`:

| | Mock (default) | Stripe |
|---|---|---|
| Dependency | None — pure Python, deterministic, no network | `stripe` SDK, **lazily imported** only when this provider is actually selected (the app runs fine with `stripe` uninstalled if `SEO_BILLING_PROVIDER=mock`) |
| Checkout | Returns a fake `cs_mock_...` session URL. In dev, `POST /billing/checkout` **immediately activates the plan** (`set_plan(status="active")`) — no browser round-trip needed to test upgrades locally | Creates a real Stripe Checkout Session (`mode=subscription`); plan activation happens later, asynchronously, via the webhook |
| Customer portal | Fake redirect URL | Real Stripe Billing Portal session |
| Webhook verification | None — parses the JSON body as-is (test/dev convenience) | Verifies the `Stripe-Signature` header against `SEO_STRIPE_WEBHOOK_SECRET` via `stripe.Webhook.construct_event()` |
| Required config | none | `SEO_STRIPE_API_KEY`, `SEO_STRIPE_WEBHOOK_SECRET` |

**Setting up real Stripe billing:**

1. Create a Stripe Product + Price for each paid plan. The adapter currently builds the Price lookup as `price_<plan_code>` (i.e. it expects Price IDs literally named `price_starter`, `price_pro`, `price_agency`) — either name Prices to match this convention or adjust `StripeBillingProvider.create_checkout` before go-live.
2. Set `SEO_BILLING_PROVIDER=stripe`, `SEO_STRIPE_API_KEY`, `SEO_STRIPE_WEBHOOK_SECRET`.
3. Point a Stripe webhook endpoint at `POST /api/v1/billing/webhook`, subscribed to the checkout/subscription lifecycle events.
4. **Verify event-type names against real Stripe before relying on this in production.** The handler currently matches `event["type"] in {"subscription.updated", "subscription.created", "checkout.session.completed"}`; Stripe's actual event names for subscription changes are namespaced (`customer.subscription.updated`, `customer.subscription.created`). Confirm and adjust the match set during Stripe live testing (tracked in `../SYSTEM_STATE.md` known debt).
5. `create_portal` currently passes `customer=org_id` to Stripe. In a real integration, the Stripe **customer ID** should come from `Subscription.provider_customer_id` (populated once a real Stripe customer exists for the org), not the internal `org_id` — reconcile this mapping when wiring a live account.
6. New organizations always get a `Subscription` row on creation (`status="trialing"`, `current_period_end = now + SEO_BILLING_TRIAL_DAYS`), regardless of provider — this happens in `create_organization()` so there is never a gap where an org has no subscription row to query.

### 2.4 Environment variables

None of the variables below exist yet in the repo's `.env.template` (see `../SYSTEM_STATE.md` known debt) — add them there before onboarding a new developer.

**Database**

| Variable | Default | Notes |
|---|---|---|
| `SEO_DATABASE_URL` | `sqlite:///./myseoapp.db` | Point at Postgres in any shared/production environment |
| `SEO_DB_ECHO` | `false` | SQLAlchemy statement logging |

**Auth / Identity**

| Variable | Default | Notes |
|---|---|---|
| `SEO_IDP_PROVIDER` | `dev` | `dev` \| `clerk` \| `supabase` \| `auth0` |
| `SEO_JWT_SECRET` | `change-me-in-env-super-secret` | HS256 signing secret for the dev provider — **must** be overridden outside local dev |
| `SEO_JWT_ALGORITHM` | `HS256` | |
| `SEO_ACCESS_TOKEN_TTL_MINUTES` | `60` | |
| `SEO_IDP_JWKS_URL` | *(none)* | Required for external providers |
| `SEO_IDP_ISSUER` | *(none)* | Optional, external providers |
| `SEO_IDP_AUDIENCE` | *(none)* | Optional, external providers |
| `SEO_API_KEY_PREFIX` | `msk` | Prefix on generated API key secrets |

**Billing**

| Variable | Default | Notes |
|---|---|---|
| `SEO_BILLING_PROVIDER` | `mock` | `mock` \| `stripe` |
| `SEO_STRIPE_API_KEY` | *(none)* | Required when provider is `stripe` |
| `SEO_STRIPE_WEBHOOK_SECRET` | *(none)* | Required when provider is `stripe` |
| `SEO_DEFAULT_PLAN_CODE` | `free` | Plan assigned to a brand-new organization |
| `SEO_BILLING_TRIAL_DAYS` | `14` | Trial length set on `Subscription.current_period_end` at org creation |

---

## Part 3 — Onboarding-to-Paid Flow

1. **Sign up.** `POST /auth/signup {email, password, org_name, full_name}` (dev provider) or first login through the configured external IdP. This one call creates: a `User` (password PBKDF2-hashed), an `Organization` (unique slug derived from `org_name`, `plan_code = SEO_DEFAULT_PLAN_CODE`), a `Membership` with role `owner`, and a `Subscription` in `trialing` status. The response includes a ready-to-use bearer token.
2. **Land on the free plan automatically.** No credit card, no separate "choose a plan" step is required to start using the product — quotas for the Free plan (§2.1) apply immediately.
3. **Invite the team (and clients).** An `owner`/`agency_admin` calls `POST /orgs/invites {email, role}`; the invitee redeems it with `POST /orgs/invites/accept {token}` while authenticated under *their own* account (which may be brand new, or may already own a separate organization). This is what makes the agency multi-client model work: one person can hold a `client`-role `Membership` in several agencies' organizations and an `owner`-role `Membership` in their own, and switch between them with `POST /auth/switch-org {org_id}` (mints a fresh token scoped to the chosen org).
4. **Provision an API key** (optional) for CI, scripts, or the MCP server: `POST /api-keys`, shown once, used thereafter via `X-API-Key`.
5. **Use the product against Free-plan quotas** until a real limit is hit — at which point the blocking action returns `402 quota_exceeded` or `402 feature_not_available` with a message naming exactly which metric/feature and what plan would unblock it (§2.2).
6. **Upgrade.** `GET /billing/plans` (public) to compare tiers, then `POST /billing/checkout {plan_code}` (requires `billing:manage`, i.e. `owner` only). In mock mode this activates instantly; with Stripe configured, the caller is redirected to a hosted Stripe Checkout page, and the plan activates when Stripe's webhook (`POST /billing/webhook`) confirms payment — `set_plan()` updates both the `Subscription` row and the denormalized `Organization.plan_code` that `TenantContext` reads on every subsequent request.
7. **Manage the subscription** going forward via `POST /billing/portal` (Stripe-hosted billing portal) and monitor consumption via `GET /usage`.

This loop — signup → free quotas → team/client invites → hit a limit → upgrade — is the same loop that replaces the four separate per-tool subscriptions (Screaming Frog, Surfer, Rank Math, HikeSEO) the product was originally built to consolidate; see `../HANDOFF_BRIEF.md` and `spec/PRODUCT_SPEC.md` §11 for the packaging narrative.
