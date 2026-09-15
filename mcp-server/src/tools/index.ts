/**
 * MySEOapp MCP tool definitions.
 *
 * Each tool bundles:
 *  - a Zod schema used to validate arguments at runtime (throws on bad input),
 *  - a hand-written JSON Schema used to advertise the tool's input shape to
 *    MCP clients via the `tools/list` response, and
 *  - a handler that validates its arguments, calls the MySEOapp REST API,
 *    and returns an MCP-shaped `{ content: [{ type: "text", ... }] }` result.
 *
 * Hand-writing the JSON Schema (instead of deriving it from the Zod schema
 * with a converter) keeps tool listing fully decoupled from the Zod version
 * in use and keeps the schema shape obvious at a glance.
 *
 * Every tool calls the same authenticated `/api/v1` backend (see
 * src/apiClient.ts) — no tool takes a credential as an argument; auth is
 * attached process-wide from MYSEOAPP_API_KEY / MYSEOAPP_TOKEN.
 *
 * The core SEO tools live in this file; the newer module suites live in
 * sibling files and are composed into the single `tools` registry below:
 *  - src/tools/geo.ts   — GEO: cross-LLM visibility, prompts, citations,
 *    sentiment, AI readiness.
 *  - src/tools/peo.ts   — PEO: Knowledge Graph explorer/sensor, bios,
 *    corroboration, entity schema.
 *  - src/tools/aeo.ts   — AEO: PAA questions, clusters/FAQ, schema graphs,
 *    internal links, voice audits.
 *  - src/tools/kit.ts   — Kit assistant: action plans, execution queue,
 *    keyword mapping, content calendar.
 *  - src/tools/local.ts — Local SEO: GBP posts/metrics/reviews, citation/NAP
 *    distribution.
 *  - src/tools/jobs.ts  — Background jobs: submit crawls/rank polls/report
 *    builds to the job queue, list/poll/cancel jobs.
 *  - src/tools/aitracker.ts — AI Answer-Engine Visibility Tracker: managed
 *    prompt-set configs, runs, visibility/SoV rollups, mention-gap reports.
 */

import { z } from "zod";
import { apiClient } from "../apiClient.js";
import { defineTool, type ToolDefinition } from "./define.js";
import { geoTools } from "./geo.js";
import { peoTools } from "./peo.js";
import { aeoTools } from "./aeo.js";
import { kitTools } from "./kit.js";
import { localTools } from "./local.js";
import { jobsTools } from "./jobs.js";
import { aitrackerTools } from "./aitracker.js";

export type {
  ToolCallOutput,
  ToolDefinition,
  ToolInputJsonSchema,
  ToolTextContent,
} from "./define.js";

// ---------------------------------------------------------------------------
// run_audit — POST /audit/crawl
// ---------------------------------------------------------------------------

const runAuditSchema = z.object({
  startUrl: z.string().min(1, "startUrl is required"),
  maxPages: z.number().int().positive().optional(),
  maxDepth: z.number().int().positive().optional(),
});

const runAuditTool = defineTool(
  "run_audit",
  "Crawl a website starting from a URL and run a full technical + on-page SEO audit " +
    "across the discovered pages (Screaming Frog style). Returns a crawl summary, " +
    "per-page issues, and site health metrics.",
  runAuditSchema,
  {
    type: "object",
    properties: {
      startUrl: { type: "string", description: "Absolute URL to start crawling from, e.g. https://example.com" },
      maxPages: { type: "integer", minimum: 1, description: "Maximum number of pages to crawl" },
      maxDepth: { type: "integer", minimum: 1, description: "Maximum link depth to follow from the start URL" },
    },
    required: ["startUrl"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/audit/crawl", args)
);

// ---------------------------------------------------------------------------
// audit_page — POST /audit/page
// ---------------------------------------------------------------------------

const auditPageSchema = z.object({
  url: z.string().min(1).optional(),
  html: z.string().min(1).optional(),
});

const auditPageTool = defineTool(
  "audit_page",
  "Run a single-page SEO audit against a live URL or raw HTML, checking technical SEO " +
    "signals such as titles, meta tags, headings, links, images, and structured data.",
  auditPageSchema,
  {
    type: "object",
    properties: {
      url: { type: "string", description: "Absolute URL of the page to fetch and audit" },
      html: { type: "string", description: "Raw HTML to audit directly, instead of fetching a URL" },
    },
    required: [],
    additionalProperties: false,
  },
  (args) => apiClient.post("/audit/page", args)
);

// ---------------------------------------------------------------------------
// analyze_onpage — POST /onpage/analyze
// ---------------------------------------------------------------------------

const analyzeOnpageSchema = z.object({
  targetKeyword: z.string().min(1, "targetKeyword is required"),
  html: z.string().optional(),
  content: z.string().optional(),
  title: z.string().optional(),
  metaDescription: z.string().optional(),
  url: z.string().optional(),
});

const analyzeOnpageTool = defineTool(
  "analyze_onpage",
  "Analyze on-page SEO for a target keyword against page content/HTML (Surfer/Rank Math " +
    "style): keyword usage and density, title/meta checks, readability, and optimization " +
    "suggestions.",
  analyzeOnpageSchema,
  {
    type: "object",
    properties: {
      targetKeyword: { type: "string", description: "Primary keyword to optimize the page for" },
      html: { type: "string", description: "Raw HTML of the page to analyze" },
      content: { type: "string", description: "Plain-text body content of the page to analyze" },
      title: { type: "string", description: "Page <title> to analyze" },
      metaDescription: { type: "string", description: "Page meta description to analyze" },
      url: { type: "string", description: "URL the content belongs to, for context/reporting" },
    },
    required: ["targetKeyword"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/onpage/analyze", args)
);

// ---------------------------------------------------------------------------
// content_score — POST /onpage/content-score
// ---------------------------------------------------------------------------

const contentScoreSchema = z.object({
  targetKeyword: z.string().min(1, "targetKeyword is required"),
  content: z.string().min(1, "content is required"),
  competitorTexts: z.array(z.string()).optional(),
});

const contentScoreTool = defineTool(
  "content_score",
  "Score content quality and keyword optimization for a target keyword, optionally " +
    "benchmarked against competitor texts, returning an actionable content score.",
  contentScoreSchema,
  {
    type: "object",
    properties: {
      targetKeyword: { type: "string", description: "Primary keyword the content targets" },
      content: { type: "string", description: "Full plain-text content to score" },
      competitorTexts: {
        type: "array",
        description: "Optional competitor page texts to benchmark against",
        items: { type: "string" },
      },
    },
    required: ["targetKeyword", "content"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/onpage/content-score", args)
);

// ---------------------------------------------------------------------------
// generate_schema — POST /onpage/schema
// ---------------------------------------------------------------------------

const generateSchemaSchema = z.object({
  schemaType: z.string().min(1, "schemaType is required"),
  fields: z.record(z.string(), z.unknown()),
});

const generateSchemaTool = defineTool(
  "generate_schema",
  "Generate JSON-LD structured data (schema.org markup) for a given schema type " +
    "(e.g. Article, Product, FAQPage, LocalBusiness) from supplied field values.",
  generateSchemaSchema,
  {
    type: "object",
    properties: {
      schemaType: { type: "string", description: "schema.org type to generate, e.g. Article, Product, FAQPage" },
      fields: {
        type: "object",
        description: "Field values to populate the schema with (shape depends on schemaType)",
      },
    },
    required: ["schemaType", "fields"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/onpage/schema", args)
);

// ---------------------------------------------------------------------------
// keyword_research — POST /keywords/research
// ---------------------------------------------------------------------------

const keywordResearchSchema = z.object({
  seed: z.string().min(1, "seed is required"),
  country: z.string().optional(),
  limit: z.number().int().positive().optional(),
});

const keywordResearchTool = defineTool(
  "keyword_research",
  "Research keyword ideas from a seed keyword: search volume, difficulty, and related " +
    "terms for a target country.",
  keywordResearchSchema,
  {
    type: "object",
    properties: {
      seed: { type: "string", description: "Seed keyword or phrase to expand from" },
      country: { type: "string", description: "ISO country code to scope results to, e.g. US, GB" },
      limit: { type: "integer", minimum: 1, description: "Maximum number of keyword ideas to return" },
    },
    required: ["seed"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/keywords/research", args)
);

// ---------------------------------------------------------------------------
// analyze_serp — POST /keywords/serp
// ---------------------------------------------------------------------------

const analyzeSerpSchema = z.object({
  keyword: z.string().min(1, "keyword is required"),
  country: z.string().optional(),
  device: z.enum(["desktop", "mobile", "tablet"]).optional(),
});

const analyzeSerpTool = defineTool(
  "analyze_serp",
  "Analyze the current search engine results page (SERP) for a keyword in a given " +
    "country/device, returning ranking URLs, SERP features, and competitor signals.",
  analyzeSerpSchema,
  {
    type: "object",
    properties: {
      keyword: { type: "string", description: "Keyword to fetch SERP results for" },
      country: { type: "string", description: "ISO country code to scope results to, e.g. US, GB" },
      device: { type: "string", enum: ["desktop", "mobile", "tablet"], description: "Device to simulate for the SERP snapshot" },
    },
    required: ["keyword"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/keywords/serp", args)
);

// ---------------------------------------------------------------------------
// track_rankings — POST /rankings/track
// ---------------------------------------------------------------------------

const trackRankingsSchema = z.object({
  domain: z.string().min(1, "domain is required"),
  keywords: z.array(z.string().min(1)).min(1, "at least one keyword is required"),
  country: z.string().optional(),
});

const trackRankingsTool = defineTool(
  "track_rankings",
  "Track keyword rankings for a domain across one or more keywords in a target country " +
    "(HikeSEO-style rank tracking).",
  trackRankingsSchema,
  {
    type: "object",
    properties: {
      domain: { type: "string", description: "Domain to track rankings for, e.g. example.com" },
      keywords: {
        type: "array",
        description: "Keywords to track rankings for",
        items: { type: "string" },
      },
      country: { type: "string", description: "ISO country code to scope tracking to, e.g. US, GB" },
    },
    required: ["domain", "keywords"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/rankings/track", args)
);

// ---------------------------------------------------------------------------
// generate_report — POST /reports/build
// ---------------------------------------------------------------------------

const generateReportSchema = z.object({
  site: z.string().min(1, "site is required"),
  crawlId: z.string().optional(),
  domain: z.string().optional(),
  periodStart: z.string().optional(),
  periodEnd: z.string().optional(),
});

const generateReportTool = defineTool(
  "generate_report",
  "Build an SEO performance report for a site/domain, optionally scoped to a specific " +
    "crawl and date range.",
  generateReportSchema,
  {
    type: "object",
    properties: {
      site: { type: "string", description: "Site identifier or base URL the report is for" },
      crawlId: { type: "string", description: "Optional crawl ID to scope the report to a specific audit run" },
      domain: { type: "string", description: "Optional domain to scope ranking/report data to" },
      periodStart: { type: "string", description: "Optional ISO-8601 start date for the report period" },
      periodEnd: { type: "string", description: "Optional ISO-8601 end date for the report period" },
    },
    required: ["site"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/reports/build", args)
);

// ---------------------------------------------------------------------------
// account_usage — GET /usage
// ---------------------------------------------------------------------------

const accountUsageSchema = z.object({});

const accountUsageTool = defineTool(
  "account_usage",
  "Get the authenticated organization's current monthly usage and plan limits " +
    "(crawls, content scores, keyword lookups, reports, sites, tracked keywords) from the " +
    "MySEOapp backend. Takes no arguments — the organization is resolved from the request's " +
    "auth (X-API-Key or Authorization: Bearer). Useful for checking headroom before a large " +
    "run_audit/keyword_research call, or after a 402 quota error from another tool.",
  accountUsageSchema,
  {
    type: "object",
    properties: {},
    required: [],
    additionalProperties: false,
  },
  () => apiClient.get("/usage")
);

// ---------------------------------------------------------------------------

/** The core SEO tools defined in this file. */
const coreTools: ToolDefinition[] = [
  runAuditTool,
  auditPageTool,
  analyzeOnpageTool,
  contentScoreTool,
  generateSchemaTool,
  keywordResearchTool,
  analyzeSerpTool,
  trackRankingsTool,
  generateReportTool,
  accountUsageTool,
];

/** All MySEOapp tools exposed by this MCP server. */
export const tools: ToolDefinition[] = [
  ...coreTools,
  ...geoTools,
  ...peoTools,
  ...aeoTools,
  ...kitTools,
  ...localTools,
  ...jobsTools,
  ...aitrackerTools,
];
