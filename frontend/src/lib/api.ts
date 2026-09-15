/**
 * Typed REST client for the MySEOapp backend.
 *
 * Base URL resolves from `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`);
 * every route is mounted under the `/api/v1` prefix. Interfaces below mirror the
 * backend Pydantic models field-for-field (see backend/app/models/*.py) so the
 * wire format (snake_case JSON) matches exactly.
 *
 * Every exported function returns a typed `Promise` and throws a typed `ApiError`
 * on failure (never a bare `unknown`/`any`), so callers can safely do:
 *
 *   try {
 *     data = await api.keywordResearch({ seed });
 *   } catch {
 *     data = mock.mockKeywordResearchResult;
 *   }
 *
 * Auth: `setAuthToken()` stores the current bearer token (in module state only —
 * see `@/lib/auth` for the React context that persists it to localStorage and
 * keeps it in sync). Every request automatically sends
 * `Authorization: Bearer <token>` once a token is set. 401/402/403 responses are
 * also broadcast to a single subscriber (`setApiAuthEventListener`) so one place
 * (the AuthProvider) can redirect to /login, surface an upgrade prompt, or show
 * a "you lack permission" notice — without every page having to special-case it.
 */

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

export const API_BASE_URL =
  (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(/\/+$/, "");

export const API_PREFIX = "/api/v1";

// ---------------------------------------------------------------------------
// Shared enums & primitives (mirrors backend/app/models/common.py)
// ---------------------------------------------------------------------------

export type Severity = "critical" | "high" | "medium" | "low" | "info";

export type IssueCategory =
  | "technical"
  | "on_page"
  | "content"
  | "links"
  | "images"
  | "indexability"
  | "performance"
  | "structured_data"
  | "international"
  | "security"
  | "mobile"
  | "local";

export type Device = "desktop" | "mobile";

export type SearchIntent = "informational" | "navigational" | "commercial" | "transactional";

export type Indexability = "indexable" | "non_indexable";

export interface Issue {
  code: string;
  title: string;
  description: string;
  category: IssueCategory;
  severity: Severity;
  recommendation: string;
  url: string | null;
  details: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Audit / crawl (mirrors backend/app/models/audit.py)
// ---------------------------------------------------------------------------

export interface CrawlConfig {
  start_url: string;
  max_pages: number;
  max_depth: number;
  respect_robots: boolean;
  follow_external: boolean;
  render_js: boolean;
  user_agent: string;
  include_patterns: string[];
  exclude_patterns: string[];
}

export interface RedirectHop {
  url: string;
  status_code: number;
  location: string | null;
}

export interface LinkInfo {
  source_url: string;
  target_url: string;
  anchor_text: string;
  rel: string;
  is_internal: boolean;
  status_code: number | null;
}

export interface ImageInfo {
  src: string;
  alt: string | null;
  has_alt: boolean;
}

export interface HreflangEntry {
  lang: string;
  href: string;
}

export interface PageAuditResult {
  url: string;
  final_url: string;
  status_code: number;
  content_type: string;
  response_time_ms: number;
  depth: number;
  discovered_from: string | null;

  title: string | null;
  title_length: number;
  meta_description: string | null;
  meta_description_length: number;
  meta_robots: string | null;
  x_robots_tag: string | null;
  canonical: string | null;
  indexability: Indexability;
  indexability_reason: string | null;

  h1: string[];
  h2: string[];
  word_count: number;
  lang: string | null;
  hreflang: HreflangEntry[];
  structured_data_types: string[];

  internal_links_count: number;
  external_links_count: number;
  outlinks: LinkInfo[];
  broken_links: LinkInfo[];
  images_count: number;
  images_missing_alt: number;

  redirect_chain: RedirectHop[];

  issues: Issue[];
  score: number;
}

export interface CrawlSummary {
  total_pages: number;
  by_status_class: Record<string, number>;
  by_severity: Record<string, number>;
  indexable_pages: number;
  non_indexable_pages: number;
  pages_with_issues: number;
  avg_score: number;
  broken_links_total: number;
  missing_titles: number;
  duplicate_titles: number;
  missing_meta_descriptions: number;
}

export interface CrawlResult {
  crawl_id: string;
  start_url: string;
  config: CrawlConfig;
  started_at: string;
  finished_at: string | null;
  pages: PageAuditResult[];
  summary: CrawlSummary;
  top_issues: Issue[];
}

// ---------------------------------------------------------------------------
// On-page / content (mirrors backend/app/models/onpage.py)
// ---------------------------------------------------------------------------

export type CheckCategory =
  | "basic_seo"
  | "additional_seo"
  | "title_readability"
  | "content_readability";

export interface OnPageCheck {
  code: string;
  label: string;
  category: CheckCategory;
  passed: boolean;
  weight: number;
  message: string;
}

export interface OnPageResult {
  target_keyword: string;
  score: number;
  grade: string;
  passed_count: number;
  total_count: number;
  checks: OnPageCheck[];
  issues: Issue[];
  category_scores: Record<string, number>;
}

export type TermStatus = "under" | "optimal" | "over";

export interface TermTarget {
  term: string;
  current_count: number;
  recommended_min: number;
  recommended_max: number;
  status: TermStatus;
  in_headings: boolean;
  importance: number;
}

export interface ContentScore {
  target_keyword: string;
  content_score: number;
  seo_score: number;
  ai_search_score: number | null;
  word_count: number;
  word_count_target_min: number;
  word_count_target_max: number;
  headings_count: number;
  headings_target: number;
  images_count: number;
  images_target: number;
  term_targets: TermTarget[];
  missing_terms: string[];
  overused_terms: string[];
  suggestions: string[];
}

// ---------------------------------------------------------------------------
// Keywords / SERP / rankings (mirrors backend/app/models/keywords.py)
// ---------------------------------------------------------------------------

export type SerpFeature =
  | "featured_snippet"
  | "people_also_ask"
  | "local_pack"
  | "image_pack"
  | "video"
  | "shopping"
  | "ai_overview"
  | "knowledge_panel"
  | "sitelinks"
  | "top_stories";

export interface Keyword {
  keyword: string;
  search_volume: number;
  difficulty: number;
  cpc: number;
  competition: number;
  intent: SearchIntent;
  parent_topic: string | null;
  serp_features: SerpFeature[];
}

export interface KeywordCluster {
  name: string;
  keywords: Keyword[];
  total_volume: number;
  avg_difficulty: number;
}

export interface KeywordResearchResult {
  seed: string;
  country: string;
  keywords: Keyword[];
  clusters: KeywordCluster[];
  total_keywords: number;
}

export interface SerpResultItem {
  position: number;
  url: string;
  domain: string;
  title: string;
  snippet: string;
  word_count: number | null;
  backlinks: number | null;
}

export interface SerpAnalysis {
  keyword: string;
  country: string;
  device: Device;
  results: SerpResultItem[];
  features: SerpFeature[];
  avg_word_count: number;
  avg_backlinks: number;
  difficulty: number;
}

export interface RankPoint {
  day: string;
  position: number | null;
  url: string | null;
}

export interface TrackedKeyword {
  keyword: string;
  domain: string;
  country: string;
  device: Device;
  search_volume: number;
  current_position: number | null;
  previous_position: number | null;
  best_position: number | null;
  history: RankPoint[];
}

export interface RankTrackingSummary {
  domain: string;
  country: string;
  total_keywords: number;
  avg_position: number;
  improved: number;
  declined: number;
  unchanged: number;
  top3: number;
  top10: number;
  visibility_score: number;
  keywords: TrackedKeyword[];
}

// ---------------------------------------------------------------------------
// Action plans / reporting (mirrors backend/app/models/reporting.py)
// ---------------------------------------------------------------------------

export type TaskStatus = "todo" | "in_progress" | "done" | "flagged";
export type Effort = "low" | "medium" | "high";

export interface AiReview {
  verdict: string;
  reasoning: string;
  confidence: number;
}

export interface Task {
  id: string;
  title: string;
  description: string;
  category: IssueCategory;
  priority: Severity;
  status: TaskStatus;
  page_url: string | null;
  keyword: string | null;
  impact: number;
  effort: Effort;
  ai_review: AiReview | null;
}

export interface ActionPlan {
  site: string;
  generated_at: string;
  tasks: Task[];
  total: number;
  by_priority: Record<string, number>;
  by_status: Record<string, number>;
}

export interface WhiteLabelBranding {
  agency_name: string;
  logo_url: string | null;
  primary_color: string;
  accent_color: string;
  footer_text: string;
  agent_name: string;
  agent_icon_url: string | null;
  contact_email: string | null;
}

export interface ReportSection {
  title: string;
  type: string;
  summary: string;
  data: Record<string, unknown>;
}

export interface Report {
  report_id: string;
  site: string;
  period_start: string;
  period_end: string;
  generated_at: string;
  branding: WhiteLabelBranding;
  sections: ReportSection[];
  headline_metrics: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Integrations (mirrors backend/app/models/integrations.py)
// ---------------------------------------------------------------------------

export type DeliveryStatus =
  | "pending"
  | "validated"
  | "sent"
  | "delivered"
  | "failed"
  | "rejected";

export interface LeadRecord {
  id: string | null;
  name: string;
  email: string;
  phone: string | null;
  company: string | null;
  website: string | null;
  source: string;
  message: string | null;
  custom_fields: Record<string, unknown>;
  created_at: string | null;
}

export interface LeadValidationResult {
  valid: boolean;
  normalized: LeadRecord | null;
  errors: string[];
  warnings: string[];
}

export interface DeliveryLog {
  id: string;
  target: string;
  lead_id: string | null;
  status: DeliveryStatus;
  attempts: number;
  last_error: string | null;
  created_at: string;
  updated_at: string;
  response_ref: string | null;
}

// ---------------------------------------------------------------------------
// Auth / identity (mirrors backend/app/api/routes_auth.py)
// ---------------------------------------------------------------------------

/** Role names, ascending privilege: client < editor < agency_admin < owner. */
export type Role = "owner" | "agency_admin" | "editor" | "client";

export interface AuthUserSummary {
  id: string;
  email: string;
  /** Only present on the /auth/signup response. */
  full_name?: string;
}

export interface AuthOrgSummary {
  id: string;
  name: string;
  plan_code: string;
  role: string;
}

export interface AuthMembershipSummary {
  org_id: string;
  role: string;
}

/** Response shape shared by POST /auth/signup and POST /auth/login. */
export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: AuthUserSummary;
  org: AuthOrgSummary;
  /** Only present on the /auth/login response (every org this user belongs to). */
  memberships?: AuthMembershipSummary[];
}

/** Response shape for POST /auth/switch-org — same token contract, no `user`. */
export interface SwitchOrgResponse {
  access_token: string;
  token_type: string;
  org: AuthOrgSummary;
}

export interface MeResponse {
  user_id: string;
  email: string | null;
  org_id: string;
  org_name: string;
  role: string;
  plan_code: string;
  auth_method: string;
}

export interface SignupArgs {
  email: string;
  password: string;
  full_name?: string;
  org_name?: string;
}

export interface LoginArgs {
  email: string;
  password: string;
}

export interface SwitchOrgArgs {
  org_id: string;
}

// ---------------------------------------------------------------------------
// Organizations / members / invites (mirrors backend/app/api/routes_orgs.py)
// ---------------------------------------------------------------------------

export interface Org {
  id: string;
  name: string;
  slug: string;
  plan_code: string;
  role: string;
}

export interface OrgSubscriptionSummary {
  plan_code: string;
  status: string;
}

export interface CurrentOrg {
  id: string;
  name: string;
  plan_code: string;
  role: string;
  subscription: OrgSubscriptionSummary | null;
}

export interface Member {
  user_id: string;
  email: string | null;
  role: string;
  status: string;
}

export interface Invite {
  id: string;
  email: string;
  role: string;
  token: string;
  expires_at: string | null;
}

export interface CreateOrgArgs {
  name: string;
}

export interface InviteArgs {
  email: string;
  role?: string;
}

export interface AcceptInviteArgs {
  token: string;
}

export interface AcceptInviteResult {
  org_id: string;
  role: string;
}

// ---------------------------------------------------------------------------
// API keys (mirrors backend/app/api/routes_apikeys.py)
// ---------------------------------------------------------------------------

export interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  last4: string;
  role: string;
  revoked: boolean;
  created_at: string;
  last_used_at: string | null;
}

/** Only returned once, at creation time — the full secret is never shown again. */
export interface CreateApiKeyResult {
  id: string;
  name: string;
  secret: string;
  prefix: string;
  last4: string;
  role: string;
  note: string;
}

export interface CreateApiKeyArgs {
  name?: string;
  role?: string;
}

export interface RevokeApiKeyResult {
  id: string;
  revoked: boolean;
}

// ---------------------------------------------------------------------------
// Billing: plans, subscription, checkout (mirrors backend/app/billing/*.py,
// backend/app/api/routes_billing.py)
// ---------------------------------------------------------------------------

/** Plan feature flags — gate UI affordances like white-label branding. */
export type PlanFeature =
  | "white_label"
  | "api_access"
  | "mcp_access"
  | "content_ai"
  | "competitor_analysis"
  | "scheduled_crawls"
  | "priority_support";

export interface PlanLimits {
  sites: number;
  tracked_keywords: number;
  crawls_per_month: number;
  pages_per_crawl: number;
  content_scores_per_month: number;
  keyword_lookups_per_month: number;
  reports_per_month: number;
  seats: number;
}

export interface Plan {
  code: string;
  name: string;
  price_monthly: number;
  price_annual: number;
  description: string;
  limits: PlanLimits;
  /** Feature flag strings, e.g. "white_label". Sorted alphabetically by the API. */
  features: string[];
  is_custom: boolean;
}

export interface Subscription {
  plan_code: string;
  status: string;
  provider: string;
  current_period_end: string | null;
  seats: number;
  plan: Plan;
}

export interface CheckoutArgs {
  plan_code: string;
  success_url?: string;
  cancel_url?: string;
}

export interface CheckoutResult {
  checkout_url: string;
  provider: string;
  session_id: string;
}

export interface BillingPortalResult {
  portal_url: string;
}

// ---------------------------------------------------------------------------
// Usage / quotas (mirrors backend/app/api/routes_usage.py)
// ---------------------------------------------------------------------------

export interface UsageMetric {
  used: number;
  limit: number;
}

export interface MonthlyUsage {
  crawls_per_month: UsageMetric;
  content_scores_per_month: UsageMetric;
  keyword_lookups_per_month: UsageMetric;
  reports_per_month: UsageMetric;
}

export interface ResourceUsage {
  sites: UsageMetric;
  tracked_keywords: UsageMetric;
}

export interface Usage {
  plan_code: string;
  monthly: MonthlyUsage;
  resources: ResourceUsage;
}

// ---------------------------------------------------------------------------
// Request DTOs — only the fields our client functions accept as input.
// Fields the backend defaults server-side are optional here.
// ---------------------------------------------------------------------------

export interface AuditPageArgs {
  url: string;
  render_js?: boolean;
}

export interface RunCrawlArgs extends Partial<Omit<CrawlConfig, "start_url">> {
  start_url: string;
}

export interface AnalyzeOnpageArgs {
  target_keyword: string;
  url?: string;
  html?: string;
  title?: string;
  meta_description?: string;
  content?: string;
  secondary_keywords?: string[];
}

export interface ContentScoreArgs {
  target_keyword: string;
  content?: string;
  country?: string;
  secondary_keywords?: string[];
  competitor_word_counts?: number[];
}

export interface KeywordResearchArgs {
  seed: string;
  country?: string;
  language?: string;
  limit?: number;
  include_questions?: boolean;
}

export interface AnalyzeSerpArgs {
  keyword: string;
  country?: string;
  device?: Device;
}

export interface TrackRankingsArgs {
  domain: string;
  keywords: string[];
  country?: string;
  device?: Device;
}

export interface GetRankingsArgs {
  domain: string;
  country?: string;
}

export interface BuildReportArgs {
  site: string;
  period_start: string;
  period_end: string;
  branding?: Partial<WhiteLabelBranding>;
  /** Optional live-data sources the backend will pull into the report. */
  crawl_id?: string;
  domain?: string;
  country?: string;
  /** @deprecated no longer read by the backend; harmless to omit. */
  section_types?: string[];
}

export interface SubmitLeadArgs {
  name?: string;
  email: string;
  phone?: string;
  company?: string;
  website?: string;
  source?: string;
  message?: string;
  custom_fields?: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Error handling
// ---------------------------------------------------------------------------

/** Thrown by every client function on network failure or a non-2xx response. */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(message: string, status: number, detail = "") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

/** Best-effort extraction of a human-readable message from an error payload. */
function extractErrorMessage(payload: unknown, fallback: string): string {
  if (isRecord(payload)) {
    if (typeof payload.detail === "string") return payload.detail;
    if (typeof payload.error === "string") return payload.error;
    if (typeof payload.message === "string") return payload.message;
  }
  return fallback;
}

// ---------------------------------------------------------------------------
// Auth token store + global 401/402/403 event bus
// ---------------------------------------------------------------------------
//
// `authToken` is module-level state. That is safe here because it is only ever
// *written* from client-side code (see `@/lib/auth`'s AuthProvider, a "use
// client" component) — on the server this module is evaluated fresh per
// request/process and nothing server-side ever calls `setAuthToken`, so the
// server-rendered copy stays `null` forever and no state leaks between users.

let authToken: string | null = null;

/** Set (or clear, with `null`) the bearer token attached to every request. */
export function setAuthToken(token: string | null): void {
  authToken = token;
}

/** Read the current in-memory bearer token (mainly for tests/debugging). */
export function getAuthToken(): string | null {
  return authToken;
}

export interface ApiAuthEvent {
  status: 401 | 402 | 403;
  error: ApiError;
  path: string;
}

export type ApiAuthEventListener = (event: ApiAuthEvent) => void;

let authEventListener: ApiAuthEventListener | null = null;

/**
 * Register a single listener notified whenever any request (that hasn't opted
 * out via `suppressAuthEvents`) receives a 401/402/403. The AuthProvider uses
 * this to redirect to /login (401), surface an "upgrade your plan" prompt
 * (402), or a "you lack permission" notice (403) from one place, so individual
 * pages don't need to special-case auth failures.
 */
export function setApiAuthEventListener(listener: ApiAuthEventListener | null): void {
  authEventListener = listener;
}

// ---------------------------------------------------------------------------
// Core fetch wrapper
// ---------------------------------------------------------------------------

export type QueryParams = Record<string, string | number | boolean | undefined>;

function buildUrl(path: string, params?: QueryParams): string {
  const url = new URL(`${API_BASE_URL}${API_PREFIX}${path}`);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  params?: QueryParams;
  signal?: AbortSignal;
  /**
   * Skip the global 401/402/403 broadcast for this call. Used by
   * login/signup (a bad password is expected 401 territory, not a "your
   * session died" event) and switch-org (a failed switch shouldn't log the
   * user out of their *current* org).
   */
  suppressAuthEvents?: boolean;
}

async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, params, signal, suppressAuthEvents = false } = options;
  const url = buildUrl(path, params);

  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (authToken) headers.Authorization = `Bearer ${authToken}`;

  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers: Object.keys(headers).length > 0 ? headers : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
      cache: "no-store",
    });
  } catch (cause) {
    const message = cause instanceof Error ? cause.message : "Network request failed";
    throw new ApiError(`Unable to reach the API at ${API_BASE_URL} (${message})`, 0);
  }

  const text = await response.text();
  let payload: unknown = undefined;
  if (text) {
    try {
      payload = JSON.parse(text) as unknown;
    } catch {
      payload = undefined;
    }
  }

  if (!response.ok) {
    const error = new ApiError(
      extractErrorMessage(payload, `Request failed with status ${response.status}`),
      response.status,
      isRecord(payload) && typeof payload.detail === "string" ? payload.detail : "",
    );
    if (!suppressAuthEvents && (response.status === 401 || response.status === 402 || response.status === 403)) {
      authEventListener?.({ status: response.status, error, path });
    }
    throw error;
  }

  return payload as T;
}

// ---------------------------------------------------------------------------
// Public API — one function per backend capability
// ---------------------------------------------------------------------------

/** Audit a single URL: fetch + analyze one page (technical + on-page signals). */
export function auditPage(args: AuditPageArgs): Promise<PageAuditResult> {
  return apiRequest<PageAuditResult>("/audit/page", { method: "POST", body: args });
}

/** Kick off a full site crawl starting from `start_url`. */
export function runCrawl(args: RunCrawlArgs): Promise<CrawlResult> {
  return apiRequest<CrawlResult>("/audit/crawl", { method: "POST", body: args });
}

/** Run the rule-based on-page checklist against a page/content draft. */
export function analyzeOnpage(args: AnalyzeOnpageArgs): Promise<OnPageResult> {
  return apiRequest<OnPageResult>("/onpage/analyze", { method: "POST", body: args });
}

/** Surfer-style content score with term targets, derived from SERP competitors. */
export function contentScore(args: ContentScoreArgs): Promise<ContentScore> {
  return apiRequest<ContentScore>("/onpage/content-score", { method: "POST", body: args });
}

/** Expand a seed keyword into a full table with volume/difficulty/intent + clusters. */
export function keywordResearch(args: KeywordResearchArgs): Promise<KeywordResearchResult> {
  return apiRequest<KeywordResearchResult>("/keywords/research", { method: "POST", body: args });
}

/** Pull the live SERP + competitor signals for a single keyword. */
export function analyzeSerp(args: AnalyzeSerpArgs): Promise<SerpAnalysis> {
  return apiRequest<SerpAnalysis>("/keywords/serp", { method: "POST", body: args });
}

/** Add/refresh a set of keywords in rank tracking for a domain. */
export function trackRankings(args: TrackRankingsArgs): Promise<RankTrackingSummary> {
  return apiRequest<RankTrackingSummary>("/rankings/track", { method: "POST", body: args });
}

/** Fetch the current rank-tracking summary for a domain. */
export function getRankings(args: GetRankingsArgs): Promise<RankTrackingSummary> {
  return apiRequest<RankTrackingSummary>(`/rankings/${encodeURIComponent(args.domain)}`, {
    method: "GET",
    params: { country: args.country },
  });
}

/** Generate a white-label client report for a site + period. */
export function buildReport(args: BuildReportArgs): Promise<Report> {
  return apiRequest<Report>("/reports/build", { method: "POST", body: args, params: { format: "json" } });
}

/** Submit a lead (e.g. from a mini-audit widget) for validation + CRM delivery. */
export function submitLead(args: SubmitLeadArgs): Promise<LeadValidationResult> {
  return apiRequest<LeadValidationResult>("/integrations/leads", { method: "POST", body: args });
}

/** List outbound delivery attempts (CRM / Make.com / webhooks). */
export function listDeliveries(): Promise<DeliveryLog[]> {
  return apiRequest<DeliveryLog[]>("/integrations/deliveries", { method: "GET" });
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

/** Create a user + their first organization (dev/local identity provider only). */
export function signup(args: SignupArgs): Promise<AuthResponse> {
  return apiRequest<AuthResponse>("/auth/signup", { method: "POST", body: args, suppressAuthEvents: true });
}

/** Exchange email/password for a bearer token scoped to the user's first org. */
export function login(args: LoginArgs): Promise<AuthResponse> {
  return apiRequest<AuthResponse>("/auth/login", { method: "POST", body: args, suppressAuthEvents: true });
}

/** Resolve the caller's identity from the current bearer token. */
export function getMe(): Promise<MeResponse> {
  return apiRequest<MeResponse>("/auth/me", { method: "GET" });
}

/** Mint a new token scoped to a different org this user belongs to. */
export function switchOrg(args: SwitchOrgArgs): Promise<SwitchOrgResponse> {
  return apiRequest<SwitchOrgResponse>("/auth/switch-org", {
    method: "POST",
    body: args,
    suppressAuthEvents: true,
  });
}

// ---------------------------------------------------------------------------
// Organizations / members / invites
// ---------------------------------------------------------------------------

/** Every organization the current user is a member of. */
export function listOrgs(): Promise<Org[]> {
  return apiRequest<Org[]>("/orgs", { method: "GET" });
}

/** Create a new organization owned by the current user. */
export function createOrg(args: CreateOrgArgs): Promise<Org> {
  return apiRequest<Org>("/orgs", { method: "POST", body: args });
}

/** The org bound to the current token, plus its subscription status. */
export function getCurrentOrg(): Promise<CurrentOrg> {
  return apiRequest<CurrentOrg>("/orgs/current", { method: "GET" });
}

/** List members of the current org. */
export function listMembers(): Promise<Member[]> {
  return apiRequest<Member[]>("/orgs/members", { method: "GET" });
}

/** Invite a teammate by email (requires owner/agency_admin — `members:manage`). */
export function createInvite(args: InviteArgs): Promise<Invite> {
  return apiRequest<Invite>("/orgs/invites", { method: "POST", body: args });
}

/** Accept a pending invite token, joining its organization. */
export function acceptInvite(args: AcceptInviteArgs): Promise<AcceptInviteResult> {
  return apiRequest<AcceptInviteResult>("/orgs/invites/accept", { method: "POST", body: args });
}

// ---------------------------------------------------------------------------
// API keys
// ---------------------------------------------------------------------------

/** List API keys for the current org (secrets are never included). */
export function listApiKeys(): Promise<ApiKey[]> {
  return apiRequest<ApiKey[]>("/api-keys", { method: "GET" });
}

/** Create a new API key. The `secret` in the response is shown exactly once. */
export function createApiKey(args: CreateApiKeyArgs): Promise<CreateApiKeyResult> {
  return apiRequest<CreateApiKeyResult>("/api-keys", { method: "POST", body: args });
}

/** Revoke (soft-delete) an API key by id. */
export function revokeApiKey(keyId: string): Promise<RevokeApiKeyResult> {
  return apiRequest<RevokeApiKeyResult>(`/api-keys/${encodeURIComponent(keyId)}`, { method: "DELETE" });
}

// ---------------------------------------------------------------------------
// Billing
// ---------------------------------------------------------------------------

/** Public plan catalog (no auth required). */
export function listPlans(): Promise<Plan[]> {
  return apiRequest<Plan[]>("/billing/plans", { method: "GET" });
}

/** The current org's subscription, including the resolved plan details. */
export function getSubscription(): Promise<Subscription> {
  return apiRequest<Subscription>("/billing/subscription", { method: "GET" });
}

/** Start a checkout session for a plan upgrade/downgrade (owner-only). */
export function createCheckout(args: CheckoutArgs): Promise<CheckoutResult> {
  return apiRequest<CheckoutResult>("/billing/checkout", { method: "POST", body: args });
}

/** Open the billing provider's self-serve portal (owner-only). */
export function createBillingPortal(): Promise<BillingPortalResult> {
  return apiRequest<BillingPortalResult>("/billing/portal", { method: "POST" });
}

// ---------------------------------------------------------------------------
// Usage
// ---------------------------------------------------------------------------

/** Monthly metric usage + absolute resource usage for the current org/plan. */
export function getUsage(): Promise<Usage> {
  return apiRequest<Usage>("/usage", { method: "GET" });
}

// ---------------------------------------------------------------------------
// GEO — Generative Engine Optimization (mirrors backend/app/models/geo.py)
// ---------------------------------------------------------------------------

export type AnswerEngine =
  | "chatgpt"
  | "claude"
  | "perplexity"
  | "copilot"
  | "gemini"
  | "google_ai_overviews";

export type FunnelStage = "tofu" | "mofu" | "bofu";

export type SentimentLabel = "positive" | "neutral" | "negative";

export type DomainCategory =
  | "community"
  | "encyclopedia"
  | "review_platform"
  | "qa_forum"
  | "news"
  | "blog"
  | "own_domain"
  | "other";

export interface Citation {
  url: string;
  domain: string;
  title: string;
}

export interface EngineAnswer {
  engine: AnswerEngine;
  prompt: string;
  text: string;
  ranked_list: string[];
  citations: Citation[];
}

export interface VisibilityMetrics {
  prompts_scanned: number;
  mentions: number;
  mention_frequency: number;
  share_of_voice: number;
  avg_position: number | null;
  mention_frequency_delta: number | null;
  share_of_voice_delta: number | null;
  avg_position_delta: number | null;
}

export interface EngineVisibility extends VisibilityMetrics {
  engine: AnswerEngine;
}

export interface VisibilityReport {
  brand: string;
  competitors: string[];
  scanned_on: string;
  engines: EngineVisibility[];
  overall: VisibilityMetrics;
  competitor_share_of_voice: Record<string, number>;
  answers: EngineAnswer[];
}

export interface TrackedPrompt {
  id: string;
  text: string;
  funnel_stage: FunnelStage;
  intent_tags: string[];
  volume_estimate: number;
  created_on: string;
}

export interface PromptSuggestion {
  text: string;
  funnel_stage: FunnelStage;
  intent_tags: string[];
  volume_estimate: number;
}

export interface PromptResearchResult {
  topic: string;
  suggestions: PromptSuggestion[];
  total: number;
}

export interface PromptRankPoint {
  day: string;
  rank: number | null;
}

export interface PromptEngineRank {
  engine: AnswerEngine;
  current_rank: number | null;
  previous_rank: number | null;
  best_rank: number | null;
  history: PromptRankPoint[];
}

export interface PromptTrackerEntry {
  prompt: TrackedPrompt;
  engines: PromptEngineRank[];
}

export interface PromptTrackerReport {
  brand: string;
  total_prompts: number;
  engines: AnswerEngine[];
  entries: PromptTrackerEntry[];
}

export interface EngineCitations {
  engine: AnswerEngine;
  citations: Citation[];
}

export interface DomainStats {
  domain: string;
  category: DomainCategory;
  trust_weight: number;
  citations: number;
  frequency: number;
  engines: AnswerEngine[];
  priority_score: number;
}

export interface CitationReport {
  brand: string;
  scanned_on: string;
  total_citations: number;
  engines: EngineCitations[];
  domains: DomainStats[];
}

export interface DomainTrustReport {
  total_citations: number;
  domains: DomainStats[];
}

export interface SentimentCell {
  engine: AnswerEngine;
  prompt: string;
  label: SentimentLabel;
  score: number;
}

export interface EngineSentiment {
  engine: AnswerEngine;
  avg_score: number;
  label: SentimentLabel;
}

export interface SentimentReport {
  brand: string;
  scanned_on: string;
  cells: SentimentCell[];
  per_engine: EngineSentiment[];
  overall_score: number;
  overall_label: SentimentLabel;
}

export interface AiCrawlerAccess {
  crawler: string;
  allowed: boolean;
}

export interface ReadinessCheck {
  code: string;
  label: string;
  passed: boolean;
  weight: number;
  message: string;
}

export interface ReadinessReport {
  url: string;
  score: number;
  grade: string;
  passed_count: number;
  total_count: number;
  checks: ReadinessCheck[];
  crawler_access: AiCrawlerAccess[];
  fixes: Issue[];
}

export interface VisibilityScanArgs {
  brand: string;
  competitors?: string[];
  prompts?: string[];
  engines?: AnswerEngine[];
}

export interface PromptCreateArgs {
  text: string;
  funnel_stage?: FunnelStage;
  intent_tags?: string[];
  volume_estimate?: number;
}

export interface PromptResearchArgs {
  topic: string;
  limit?: number;
}

export interface CitationScanArgs {
  brand: string;
  prompts?: string[];
  engines?: AnswerEngine[];
  own_domain?: string;
}

export interface SentimentScanArgs {
  brand: string;
  prompts?: string[];
  engines?: AnswerEngine[];
}

export interface ReadinessAuditArgs {
  url: string;
}

/** Scan brand visibility across every tracked answer engine. */
export function geoVisibilityScan(args: VisibilityScanArgs): Promise<VisibilityReport> {
  return apiRequest<VisibilityReport>("/geo/visibility/scan", { method: "POST", body: args });
}

/** List the org's tracked conversational prompt library. */
export function listGeoPrompts(): Promise<TrackedPrompt[]> {
  return apiRequest<TrackedPrompt[]>("/geo/prompts", { method: "GET" });
}

/** Add a prompt to the tracked library (stage/volume auto-classified if omitted). */
export function addGeoPrompt(args: PromptCreateArgs): Promise<TrackedPrompt> {
  return apiRequest<TrackedPrompt>("/geo/prompts", { method: "POST", body: args });
}

/** Expand a topic into suggested conversational prompts worth tracking. */
export function researchGeoPrompts(args: PromptResearchArgs): Promise<PromptResearchResult> {
  return apiRequest<PromptResearchResult>("/geo/prompts/research", { method: "POST", body: args });
}

/** Per-prompt, per-engine brand rank tracker over the prompt library. */
export function getPromptTracker(args: { brand: string }): Promise<PromptTrackerReport> {
  return apiRequest<PromptTrackerReport>("/geo/prompts/tracker", {
    method: "GET",
    params: { brand: args.brand },
  });
}

/** Scan which sources answer engines cite when discussing the brand. */
export function geoCitationsScan(args: CitationScanArgs): Promise<CitationReport> {
  return apiRequest<CitationReport>("/geo/citations/scan", { method: "POST", body: args });
}

/** Org-wide aggregated domain trust report across all citation scans. */
export function getCitationDomains(args: { own_domain?: string } = {}): Promise<DomainTrustReport> {
  return apiRequest<DomainTrustReport>("/geo/citations/domains", {
    method: "GET",
    params: { own_domain: args.own_domain },
  });
}

/** Sentiment heatmap (engine x prompt) for how AI answers portray the brand. */
export function geoSentimentScan(args: SentimentScanArgs): Promise<SentimentReport> {
  return apiRequest<SentimentReport>("/geo/sentiment/scan", { method: "POST", body: args });
}

/** AI readiness audit: llms.txt, crawler access, extractability checks. */
export function geoReadinessAudit(args: ReadinessAuditArgs): Promise<ReadinessReport> {
  return apiRequest<ReadinessReport>("/geo/readiness/audit", { method: "POST", body: args });
}

// ---------------------------------------------------------------------------
// PEO — Personal Entity Optimization (mirrors backend/app/models/peo.py)
// ---------------------------------------------------------------------------

export interface KGEntity {
  kg_mid: string;
  name: string;
  types: string[];
  description: string;
  result_score: number;
  url: string | null;
}

export interface EntitySearchResult {
  query: string;
  entities: KGEntity[];
}

export interface TrackedEntity {
  kg_mid: string;
  name: string;
  types: string[];
  description: string;
  latest_score: number;
}

export interface SensorObservation {
  observed_at: string;
  score: number;
}

export type TrendClass = "rising" | "stable" | "volatile" | "declining";

export interface SensorReport {
  kg_mid: string;
  name: string;
  observations: SensorObservation[];
  latest_score: number;
  mean_score: number;
  net_change: number;
  volatility: number;
  trend: TrendClass;
}

export type BioLength = "short" | "medium" | "long";

export interface BioVariant {
  length: BioLength;
  text: string;
  word_count: number;
  triple_count: number;
  triple_density: number;
}

export interface BioResult {
  name: string;
  variants: BioVariant[];
  warnings: string[];
}

export type SourceType = "wikipedia" | "wikidata" | "crunchbase" | "linkedin" | "own_site";

export interface SourceProfile {
  source: SourceType;
  url: string | null;
  facts: Record<string, string>;
}

export type FactStatus = "match" | "mismatch" | "missing";

export interface FactComparison {
  source: SourceType;
  fact: string;
  canonical_value: string;
  found_value: string | null;
  status: FactStatus;
}

export interface CorroborationReport {
  entity_name: string;
  consistency_score: number;
  sources_checked: number;
  comparisons: FactComparison[];
  match_count: number;
  mismatch_count: number;
  missing_count: number;
  fixes: string[];
}

export type EntityType = "Person" | "Organization";

export interface EntitySchemaResult {
  entity_type: EntityType;
  json_ld: Record<string, unknown>;
  script_tag: string;
  warnings: string[];
}

export interface EntitySearchArgs {
  query: string;
  types?: string[];
  limit?: number;
}

export interface EntityTrackArgs {
  kg_mid: string;
  name: string;
  types?: string[];
  description?: string;
}

export interface EntitySensorArgs {
  kg_mid: string;
  points?: number;
}

export interface BioBuildArgs {
  name: string;
  roles?: string[];
  organizations?: string[];
  works?: string[];
  credentials?: string[];
  location?: string;
  websites?: string[];
}

export interface CorroborationAuditArgs {
  entity_name: string;
  canonical_facts: Record<string, string>;
  profiles?: SourceProfile[];
  fetch_sources?: SourceType[];
}

export interface EntitySchemaArgs {
  entity_type: EntityType;
  name: string;
  url?: string;
  description?: string;
  same_as?: string[];
  image?: string;
  job_title?: string;
  works_for?: string;
  founder_of?: string[];
  author_of?: string[];
  alumni_of?: string[];
  logo?: string;
  founding_date?: string;
  founders?: string[];
}

/** Query the Knowledge Graph for entity candidates matching a name. */
export function searchEntities(args: EntitySearchArgs): Promise<EntitySearchResult> {
  return apiRequest<EntitySearchResult>("/peo/entities/search", { method: "POST", body: args });
}

/** Register a KGMID for org-scoped confidence tracking. */
export function trackEntity(args: EntityTrackArgs): Promise<TrackedEntity> {
  return apiRequest<TrackedEntity>("/peo/entities/track", { method: "POST", body: args });
}

/** Confidence-score time series + volatility/trend for a tracked entity. */
export function getEntitySensor(args: EntitySensorArgs): Promise<SensorReport> {
  return apiRequest<SensorReport>("/peo/entities/sensor", {
    method: "GET",
    params: { kg_mid: args.kg_mid, points: args.points },
  });
}

/** Generate authoritative short/medium/long entity bios from structured facts. */
export function buildBio(args: BioBuildArgs): Promise<BioResult> {
  return apiRequest<BioResult>("/peo/bio/build", { method: "POST", body: args });
}

/** Diff canonical facts across source profiles (Wikipedia, LinkedIn, ...). */
export function auditCorroboration(args: CorroborationAuditArgs): Promise<CorroborationReport> {
  return apiRequest<CorroborationReport>("/peo/corroboration/audit", { method: "POST", body: args });
}

/** Generate relationally-linked Person/Organization JSON-LD. */
export function generateEntitySchema(args: EntitySchemaArgs): Promise<EntitySchemaResult> {
  return apiRequest<EntitySchemaResult>("/peo/schema/entity", { method: "POST", body: args });
}

// ---------------------------------------------------------------------------
// AEO — Answer Engine Optimization (mirrors backend/app/models/aeo.py)
// ---------------------------------------------------------------------------

export interface PAAQuestion {
  question: string;
  parent: string | null;
  depth: number;
}

export interface QuestionExtractionResult {
  seed: string;
  questions: PAAQuestion[];
  autocomplete: string[];
}

export interface PageRef {
  url: string;
  title: string;
}

export interface QuestionCluster {
  label: string;
  primary_question: string;
  questions: string[];
}

export interface FaqEntry {
  question: string;
  answer_template: string;
  target_page: string | null;
}

export interface ClusterMapResult {
  clusters: QuestionCluster[];
  faq: FaqEntry[];
}

export interface QAItem {
  question: string;
  answer: string;
}

export interface HowToStep {
  name: string;
  text: string;
}

export interface HowToInput {
  name: string;
  steps: HowToStep[];
}

export interface BreadcrumbItem {
  name: string;
  url: string;
}

export interface SchemaGraphResult {
  json_ld: Record<string, unknown>;
  script_tag: string;
  node_types: string[];
  warnings: string[];
}

export interface PageDoc {
  url: string;
  title: string;
  body: string;
  existing_links?: string[];
}

export interface LinkSuggestion {
  source_url: string;
  target_url: string;
  similarity: number;
  anchor_text: string;
}

export interface LinkSuggestResult {
  suggestions: LinkSuggestion[];
  pages_analyzed: number;
}

export interface VoiceCheck {
  code: string;
  label: string;
  passed: boolean;
  weight: number;
  message: string;
}

export interface VoiceAuditResult {
  score: number;
  grade: string;
  flesch: number;
  avg_sentence_length: number;
  syllable_density: number;
  first_paragraph_words: number;
  checks: VoiceCheck[];
  fixes: string[];
}

export interface QuestionExtractArgs {
  seed: string;
  depth?: number;
  per_level?: number;
  include_autocomplete?: boolean;
  autocomplete_limit?: number;
}

export interface ClusterMapArgs {
  questions: string[];
  pages?: PageRef[];
  similarity_threshold?: number;
}

export interface SchemaGraphArgs {
  url: string;
  title: string;
  description?: string;
  breadcrumbs?: BreadcrumbItem[];
  faqs?: QAItem[];
  qa?: QAItem;
  how_to?: HowToInput;
}

export interface LinkSuggestArgs {
  pages: PageDoc[];
  similarity_threshold?: number;
  max_per_page?: number;
}

export interface VoiceAuditArgs {
  content: string;
  question?: string;
  answer_word_limit?: number;
}

/** Extract People-Also-Ask questions + autocomplete pathways for a seed. */
export function extractQuestions(args: QuestionExtractArgs): Promise<QuestionExtractionResult> {
  return apiRequest<QuestionExtractionResult>("/aeo/questions/extract", { method: "POST", body: args });
}

/** Cluster questions into topics and map them to FAQ target pages. */
export function mapClusters(args: ClusterMapArgs): Promise<ClusterMapResult> {
  return apiRequest<ClusterMapResult>("/aeo/clusters/map", { method: "POST", body: args });
}

/** Assemble a combined @graph JSON-LD block (FAQPage/QAPage/HowTo/...). */
export function buildSchemaGraph(args: SchemaGraphArgs): Promise<SchemaGraphResult> {
  return apiRequest<SchemaGraphResult>("/aeo/schema/graph", { method: "POST", body: args });
}

/** Suggest internal links between pages based on content similarity. */
export function suggestLinks(args: LinkSuggestArgs): Promise<LinkSuggestResult> {
  return apiRequest<LinkSuggestResult>("/aeo/linking/suggest", { method: "POST", body: args });
}

/** Voice-search readiness audit for a content draft. */
export function auditVoice(args: VoiceAuditArgs): Promise<VoiceAuditResult> {
  return apiRequest<VoiceAuditResult>("/aeo/voice/audit", { method: "POST", body: args });
}

// ---------------------------------------------------------------------------
// Kit assistant (mirrors backend/app/models/assistant.py)
// ---------------------------------------------------------------------------

export interface FixStep {
  number: number;
  instruction: string;
}

export interface ActionItem {
  id: string;
  title: string;
  what_it_means: string;
  why_it_matters: string;
  category: IssueCategory;
  severity: Severity;
  priority_score: number;
  page_url: string | null;
  keyword: string | null;
  source_code: string;
  steps: FixStep[];
  estimated_minutes: number;
}

export interface ActionItemPlan {
  site: string;
  generated_at: string;
  items: ActionItem[];
  total: number;
  by_severity: Record<string, number>;
}

export type ActionType =
  | "write_blog_post"
  | "update_meta_tags"
  | "publish_gbp_update"
  | "sync_directory_listing";

export type ExecutionStatus =
  | "pending"
  | "awaiting_approval"
  | "running"
  | "completed"
  | "failed";

export interface ExecutionLogEntry {
  attempt: number;
  level: string;
  message: string;
}

export interface QueuedAction {
  id: string;
  org_id: string;
  type: ActionType;
  params: Record<string, unknown>;
  status: ExecutionStatus;
  approval_required: boolean;
  attempts: number;
  max_attempts: number;
  result: Record<string, unknown> | null;
  last_error: string | null;
  logs: ExecutionLogEntry[];
  created_at: string;
  updated_at: string;
}

export interface QueueRunReport {
  org_id: string;
  executed: number;
  completed: number;
  failed: number;
  skipped_awaiting_approval: number;
  actions: QueuedAction[];
}

export interface SitePage {
  url: string;
  title?: string;
  content?: string;
}

export interface PageScore {
  url: string;
  score: number;
}

export interface KeywordAssignment {
  keyword: string;
  page_url: string | null;
  score: number;
  alternatives: PageScore[];
}

export interface CannibalizationFlag {
  keyword: string;
  primary_page: string;
  competing_pages: PageScore[];
  suggested_actions: string[];
}

export interface KeywordMapResult {
  assignments: KeywordAssignment[];
  cannibalization: CannibalizationFlag[];
  unmapped_keywords: string[];
}

export type CalendarCadence = "daily" | "weekly" | "biweekly" | "monthly";

export interface OutlineHeading {
  level: number;
  text: string;
}

export interface ArticleOutline {
  h1: string;
  headings: OutlineHeading[];
  target_keyword: string;
  supporting_keywords: string[];
  intent: SearchIntent;
  internal_links: string[];
}

export interface CalendarEntry {
  publish_date: string;
  title: string;
  cluster: string;
  outline: ArticleOutline;
}

export interface ContentCalendar {
  start_date: string;
  cadence: CalendarCadence;
  entries: CalendarEntry[];
  total: number;
}

export interface ActionPlanArgs {
  site: string;
  crawl_id?: string;
  domain?: string;
  country?: string;
  issues?: Issue[];
}

export interface EnqueueArgs {
  type: ActionType;
  params?: Record<string, unknown>;
  approval_required?: boolean;
  max_attempts?: number;
}

export interface KeywordMapArgs {
  keywords: string[];
  pages: SitePage[];
  cannibalization_ratio?: number;
}

export interface CalendarBuildArgs {
  keywords: Keyword[];
  start_date: string;
  cadence?: CalendarCadence;
  max_entries?: number;
  pages?: SitePage[];
}

/** Build a prioritized, plain-English action plan from audit/ranking data. */
export function buildActionPlan(args: ActionPlanArgs): Promise<ActionItemPlan> {
  return apiRequest<ActionItemPlan>("/assistant/actions/plan", { method: "POST", body: args });
}

/** List the org's agentic execution queue. */
export function listQueue(): Promise<QueuedAction[]> {
  return apiRequest<QueuedAction[]>("/assistant/queue", { method: "GET" });
}

/** Enqueue an executable action (blog post, meta tags, GBP update, ...). */
export function enqueueAction(args: EnqueueArgs): Promise<QueuedAction> {
  return apiRequest<QueuedAction>("/assistant/queue", { method: "POST", body: args });
}

/** Approve a queued action that is awaiting human sign-off. */
export function approveAction(actionId: string): Promise<QueuedAction> {
  return apiRequest<QueuedAction>(`/assistant/queue/${encodeURIComponent(actionId)}/approve`, {
    method: "POST",
  });
}

/** Run one pass of the execution loop over the org's queue. */
export function runQueue(): Promise<QueueRunReport> {
  return apiRequest<QueueRunReport>("/assistant/queue/run", { method: "POST" });
}

/** Map keywords to their most relevant pages + flag cannibalization. */
export function mapKeywords(args: KeywordMapArgs): Promise<KeywordMapResult> {
  return apiRequest<KeywordMapResult>("/assistant/keywords/map", { method: "POST", body: args });
}

/** Build a publish-ready content calendar with per-entry article outlines. */
export function buildCalendar(args: CalendarBuildArgs): Promise<ContentCalendar> {
  return apiRequest<ContentCalendar>("/assistant/calendar/build", { method: "POST", body: args });
}

// ---------------------------------------------------------------------------
// Local SEO (mirrors backend/app/models/local.py)
// ---------------------------------------------------------------------------

export interface GbpPost {
  id: string;
  org_id: string;
  summary: string;
  topic: string;
  cta_url: string | null;
  state: string;
  created_at: string;
}

export interface GbpMetrics {
  org_id: string;
  period_days: number;
  views_search: number;
  views_maps: number;
  searches_direct: number;
  searches_discovery: number;
  actions_website: number;
  actions_calls: number;
  actions_directions: number;
}

export type ReviewSentiment = "positive" | "neutral" | "negative";

export interface GbpReview {
  id: string;
  author: string;
  rating: number;
  text: string;
  created_at: string;
  reply: string | null;
}

export interface SuggestedReply {
  review_id: string;
  sentiment: ReviewSentiment;
  text: string;
}

export interface ReviewListResponse {
  reviews: GbpReview[];
  suggested_replies: SuggestedReply[];
}

export type Directory = "yelp" | "apple_maps" | "bing_places" | "foursquare";

export interface NapRecord {
  name: string;
  address: string;
  phone: string;
  website: string | null;
  hours: Record<string, string>;
  locked: boolean;
}

export interface NapDiff {
  field: string;
  expected: string;
  found: string;
}

export type ListingDeliveryState =
  | "in_sync"
  | "created"
  | "updated"
  | "failed"
  | "not_listed"
  | "drift_flagged"
  | "drift_blocked";

export interface DirectorySyncResult {
  directory: Directory;
  state: ListingDeliveryState;
  diffs: NapDiff[];
  error: string | null;
}

export interface CitationSyncReport {
  org_id: string;
  results: DirectorySyncResult[];
  delivered: number;
  failed: number;
}

export interface DirectoryStatus {
  directory: Directory;
  listed: boolean;
  drift: boolean;
  diffs: NapDiff[];
  state: ListingDeliveryState;
}

export interface CitationStatusReport {
  org_id: string;
  locked: boolean;
  drift_detected: boolean;
  directories: DirectoryStatus[];
}

export interface GbpPostCreateArgs {
  summary: string;
  topic?: string;
  cta_url?: string;
}

export interface ReviewReplyArgs {
  /** Omit/empty to use the generated suggested reply. */
  text?: string;
}

/** Publish a Google Business Profile post / update. */
export function publishGbpPost(args: GbpPostCreateArgs): Promise<GbpPost> {
  return apiRequest<GbpPost>("/local/gbp/posts", { method: "POST", body: args });
}

/** GBP search performance metrics (views, searches, customer actions). */
export function getGbpMetrics(args: { period_days?: number } = {}): Promise<GbpMetrics> {
  return apiRequest<GbpMetrics>("/local/gbp/metrics", {
    method: "GET",
    params: { period_days: args.period_days },
  });
}

/** Reviews for the org's GBP listing + generated reply suggestions. */
export function getGbpReviews(): Promise<ReviewListResponse> {
  return apiRequest<ReviewListResponse>("/local/gbp/reviews", { method: "GET" });
}

/** Reply to a review (empty text -> use the suggested reply). */
export function replyToReview(reviewId: string, args: ReviewReplyArgs = {}): Promise<GbpReview> {
  return apiRequest<GbpReview>(`/local/gbp/reviews/${encodeURIComponent(reviewId)}/reply`, {
    method: "POST",
    body: args,
  });
}

/** The canonical NAP (name/address/phone) record for the org. */
export function getNap(): Promise<NapRecord> {
  return apiRequest<NapRecord>("/local/citations/nap", { method: "GET" });
}

/** Update the canonical NAP record (with optional drift lock). */
export function putNap(args: NapRecord): Promise<NapRecord> {
  return apiRequest<NapRecord>("/local/citations/nap", { method: "PUT", body: args });
}

/** Push the canonical NAP to every (or one) supported directory. */
export function syncCitations(args: { directory?: Directory } = {}): Promise<CitationSyncReport> {
  return apiRequest<CitationSyncReport>("/local/citations/sync", {
    method: "POST",
    params: { directory: args.directory },
  });
}

/** Per-directory listing + drift status vs. the canonical NAP. */
export function getCitationStatus(): Promise<CitationStatusReport> {
  return apiRequest<CitationStatusReport>("/local/citations/status", { method: "GET" });
}

// ---------------------------------------------------------------------------
// Lead-gen widget (mirrors backend/app/api/routes_widget.py)
// ---------------------------------------------------------------------------

/** Public URL of the embeddable audit widget script for an org slug. */
export function widgetScriptUrl(orgSlug: string): string {
  return `${API_BASE_URL}${API_PREFIX}/widget/audit.js?org=${encodeURIComponent(orgSlug)}`;
}

/** Copy-paste <script> embed snippet for the lead-gen audit widget. */
export function widgetEmbedSnippet(orgSlug: string): string {
  return `<script src="${widgetScriptUrl(orgSlug)}" async></script>`;
}

// ---------------------------------------------------------------------------
// AI Tracker — v2 Answer-Engine Visibility Tracker
// (mirrors backend/app/models/aitracker.py)
// ---------------------------------------------------------------------------
//
// Plan-gated: every /ai-tracker route requires the `ai_tracker` plan feature
// and returns 402 otherwise (broadcast via the auth event bus as an upgrade
// prompt; pages should also render their own "requires Growth+" state).

/** Engines the v2 tracker queries — its own enum (adds google_ai_mode). */
export type TrackerEngine =
  | "chatgpt"
  | "perplexity"
  | "gemini"
  | "google_ai_overviews"
  | "google_ai_mode";

export type RefreshCadence = "daily" | "weekly";

export interface TrackerConfig {
  id: string;
  name: string;
  brand: string;
  prompts: string[];
  competitors: string[];
  engines: TrackerEngine[];
  market: string;
  language: string;
  own_domain: string;
  refresh_cadence: RefreshCadence;
  created_at: string;
  last_run_at: string | null;
}

/** A config due for a scheduled refresh (returned by the ops endpoint). */
export interface DueConfig {
  config_id: string;
  name: string;
  brand: string;
  refresh_cadence: RefreshCadence;
  last_run_at: string | null;
}

/** One engine answer for one prompt, parsed for brand/competitor signals. */
export interface TrackerAnswer {
  engine: TrackerEngine;
  prompt: string;
  text: string;
  ranked_list: string[];
  citations: Citation[];
  brand_mentioned: boolean;
  brand_mentions: number;
  brand_position: number | null;
  competitors_mentioned: string[];
  sentiment_label: SentimentLabel;
  sentiment_score: number;
}

/** Aggregates for one engine (or overall). Deltas are null on the first run. */
export interface RollupMetrics {
  prompts_total: number;
  prompts_mentioned: number;
  mention_rate: number;
  avg_position: number | null;
  position_score: number;
  citation_share: number;
  visibility_score: number;
  share_of_voice: number;
  competitor_share_of_voice: Record<string, number>;
  avg_sentiment: number;
  sentiment_label: SentimentLabel;
  visibility_score_delta: number | null;
  share_of_voice_delta: number | null;
  mention_rate_delta: number | null;
  /** Positive = improvement (closer to #1). */
  avg_position_delta: number | null;
}

export interface EngineRollup extends RollupMetrics {
  engine: TrackerEngine;
}

/** The per-run metrics rollup (latest one served by GET .../visibility). */
export interface VisibilityRollup {
  config_id: string;
  brand: string;
  run_at: string;
  engines: EngineRollup[];
  overall: RollupMetrics;
}

/** A prompt where competitors are mentioned but the brand is not. */
export interface MentionGapEntry {
  prompt: string;
  gap_engines: TrackerEngine[];
  competitors_mentioned: string[];
  opportunity_score: number;
}

export interface MentionGapReport {
  config_id: string;
  brand: string;
  run_at: string;
  total_prompts: number;
  entries: MentionGapEntry[];
}

/** Everything one tracker run produced: answers, rollup, mention gap. */
export interface TrackerRunReport {
  config_id: string;
  brand: string;
  run_at: string;
  engines: TrackerEngine[];
  answers: TrackerAnswer[];
  rollup: VisibilityRollup;
  mention_gap: MentionGapReport;
}

export interface TrackerConfigCreateArgs {
  name: string;
  brand: string;
  prompts?: string[];
  competitors?: string[];
  /** Empty/omitted -> the plan's full allowed engine set. */
  engines?: TrackerEngine[];
  market?: string;
  language?: string;
  /** Omitted -> derived from the brand name. */
  own_domain?: string;
  refresh_cadence?: RefreshCadence;
}

/** Partial update; omitted fields keep their current values. */
export interface TrackerConfigUpdateArgs {
  name?: string;
  brand?: string;
  prompts?: string[];
  competitors?: string[];
  /** [] -> reset to the plan default. */
  engines?: TrackerEngine[];
  market?: string;
  language?: string;
  own_domain?: string;
  refresh_cadence?: RefreshCadence;
}

export interface DeleteTrackerConfigResult {
  deleted: boolean;
  id: string;
}

/** Create a managed tracker config (named prompt set + competitors + cadence). */
export function createTrackerConfig(args: TrackerConfigCreateArgs): Promise<TrackerConfig> {
  return apiRequest<TrackerConfig>("/ai-tracker/configs", { method: "POST", body: args });
}

/** List the org's tracker configs. */
export function listTrackerConfigs(): Promise<TrackerConfig[]> {
  return apiRequest<TrackerConfig[]>("/ai-tracker/configs", { method: "GET" });
}

/** Fetch a single tracker config by id. */
export function getTrackerConfig(configId: string): Promise<TrackerConfig> {
  return apiRequest<TrackerConfig>(`/ai-tracker/configs/${encodeURIComponent(configId)}`, {
    method: "GET",
  });
}

/** Partially update a tracker config. */
export function updateTrackerConfig(
  configId: string,
  args: TrackerConfigUpdateArgs,
): Promise<TrackerConfig> {
  return apiRequest<TrackerConfig>(`/ai-tracker/configs/${encodeURIComponent(configId)}`, {
    method: "PUT",
    body: args,
  });
}

/** Delete a tracker config (and its stored runs). */
export function deleteTrackerConfig(configId: string): Promise<DeleteTrackerConfigResult> {
  return apiRequest<DeleteTrackerConfigResult>(
    `/ai-tracker/configs/${encodeURIComponent(configId)}`,
    { method: "DELETE" },
  );
}

/** Run the tracker now: query every engine, parse answers, store the rollup. */
export function runTrackerConfig(configId: string): Promise<TrackerRunReport> {
  return apiRequest<TrackerRunReport>(
    `/ai-tracker/configs/${encodeURIComponent(configId)}/run`,
    { method: "POST" },
  );
}

/** All stored run rollups for a config, oldest first. */
export function getTrackerHistory(configId: string): Promise<VisibilityRollup[]> {
  return apiRequest<VisibilityRollup[]>(
    `/ai-tracker/configs/${encodeURIComponent(configId)}/history`,
    { method: "GET" },
  );
}

/** The latest Visibility Score / Share-of-Voice rollup (404 if never run). */
export function getTrackerVisibility(configId: string): Promise<VisibilityRollup> {
  return apiRequest<VisibilityRollup>(
    `/ai-tracker/configs/${encodeURIComponent(configId)}/visibility`,
    { method: "GET" },
  );
}

/** The latest Mention-Gap report (404 if never run). */
export function getTrackerMentionGap(configId: string): Promise<MentionGapReport> {
  return apiRequest<MentionGapReport>(
    `/ai-tracker/configs/${encodeURIComponent(configId)}/mention-gap`,
    { method: "GET" },
  );
}

/** Ops endpoint: configs of this org due for a scheduled refresh (admin+). */
export function listDueTrackerConfigs(args: { now?: string } = {}): Promise<DueConfig[]> {
  return apiRequest<DueConfig[]>("/ai-tracker/due", { method: "GET", params: { now: args.now } });
}

// ---------------------------------------------------------------------------
// Jobs — background job queue (mirrors backend/app/models/jobs.py)
// ---------------------------------------------------------------------------

export type JobType = "crawl" | "rank_poll" | "report";

/** Lifecycle of a job. Terminal states: succeeded / failed / cancelled. */
export type JobStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";

/**
 * A single background job and its progress/result metadata. `result_ref`
 * points at the artifact in the existing persistence layer (crawl_id for
 * crawls, `domain|country` for rank polls, report_id for reports).
 */
export interface Job {
  id: string;
  org_id: string;
  type: JobType;
  status: JobStatus;
  progress: number;
  submitted_at: string;
  started_at: string | null;
  finished_at: string | null;
  result_ref: string | null;
  error: string | null;
  attempts: number;
}

/** Returned by the POST /jobs/* submission endpoints. */
export interface JobSubmitResponse {
  job_id: string;
  status: JobStatus;
}

/** Org-scoped job listing envelope. */
export interface JobListResponse {
  items: Job[];
  total: number;
}

/** Mirrors the /rankings/track request body. */
export interface SubmitRankPollJobArgs {
  domain: string;
  keywords: string[];
  country?: string;
  device?: Device;
  search_volumes?: Record<string, number>;
}

/** Mirrors the /reports/build request body. */
export interface SubmitReportJobArgs {
  site: string;
  period_start: string;
  period_end: string;
  branding?: Partial<WhiteLabelBranding>;
  crawl_id?: string;
  domain?: string;
  country?: string;
}

export interface ListJobsArgs {
  status?: JobStatus;
  type?: JobType;
}

/** Submit a site crawl as a background job (quota checked at submission). */
export function submitCrawlJob(args: RunCrawlArgs): Promise<JobSubmitResponse> {
  return apiRequest<JobSubmitResponse>("/jobs/crawl", { method: "POST", body: args });
}

/** Submit a rank-tracking refresh as a background job. */
export function submitRankPollJob(args: SubmitRankPollJobArgs): Promise<JobSubmitResponse> {
  return apiRequest<JobSubmitResponse>("/jobs/rank-poll", { method: "POST", body: args });
}

/** Submit a report build as a background job. */
export function submitReportJob(args: SubmitReportJobArgs): Promise<JobSubmitResponse> {
  return apiRequest<JobSubmitResponse>("/jobs/report", { method: "POST", body: args });
}

/** List the org's jobs, optionally filtered by status and/or type. */
export function listJobs(args: ListJobsArgs = {}): Promise<JobListResponse> {
  return apiRequest<JobListResponse>("/jobs", {
    method: "GET",
    params: { status: args.status, type: args.type },
  });
}

/** Poll a single job's status/progress by id. */
export function getJob(jobId: string): Promise<Job> {
  return apiRequest<Job>(`/jobs/${encodeURIComponent(jobId)}`, { method: "GET" });
}

/** Cancel a job that is still queued (no-op transition otherwise). */
export function cancelJob(jobId: string): Promise<Job> {
  return apiRequest<Job>(`/jobs/${encodeURIComponent(jobId)}/cancel`, { method: "POST" });
}
