/**
 * GEO (Generative Engine Optimization) MCP tools.
 *
 * Cross-LLM brand visibility scans, conversational prompt research/tracking,
 * citation & source-domain trust mapping, sentiment profiling, and AI
 * readiness audits — backed by the backend's /api/v1/geo/* routes.
 */

import { z } from "zod";
import { apiClient } from "../apiClient.js";
import { buildQuery, defineTool, type ToolDefinition } from "./define.js";

/** Generative answer engines the backend can scan (models/geo.py AnswerEngine). */
const ANSWER_ENGINES = [
  "chatgpt",
  "claude",
  "perplexity",
  "copilot",
  "gemini",
  "google_ai_overviews",
] as const;

const engineEnum = z.enum(ANSWER_ENGINES);

const enginesJsonSchema = {
  type: "array",
  description: "Answer engines to scan (empty/omitted = all engines)",
  items: { type: "string", enum: [...ANSWER_ENGINES] },
} as const;

const promptsJsonSchema = {
  type: "array",
  description: "Prompts to scan (empty/omitted = the org's tracked prompt library)",
  items: { type: "string" },
} as const;

// ---------------------------------------------------------------------------
// geo_visibility_scan — POST /geo/visibility/scan
// ---------------------------------------------------------------------------

const geoVisibilityScanSchema = z.object({
  brand: z.string().min(1, "brand is required"),
  competitors: z.array(z.string().min(1)).optional(),
  prompts: z.array(z.string().min(1)).optional(),
  engines: z.array(engineEnum).optional(),
});

const geoVisibilityScanTool = defineTool(
  "geo_visibility_scan",
  "Scan generative answer engines (ChatGPT, Claude, Perplexity, Copilot, Gemini, Google " +
    "AI Overviews) for brand visibility: mention frequency, share of voice vs competitors, " +
    "and average position in generated recommendation lists, per engine and overall.",
  geoVisibilityScanSchema,
  {
    type: "object",
    properties: {
      brand: { type: "string", description: "Brand name to measure visibility for" },
      competitors: {
        type: "array",
        description: "Competitor brand names for share-of-voice comparison",
        items: { type: "string" },
      },
      prompts: promptsJsonSchema,
      engines: enginesJsonSchema,
    },
    required: ["brand"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/geo/visibility/scan", args)
);

// ---------------------------------------------------------------------------
// geo_prompt_research — POST /geo/prompts/research
// ---------------------------------------------------------------------------

const geoPromptResearchSchema = z.object({
  topic: z.string().min(1, "topic is required"),
  limit: z.number().int().min(1).max(100).optional(),
});

const geoPromptResearchTool = defineTool(
  "geo_prompt_research",
  "Research conversational prompts people ask AI assistants about a topic, classified by " +
    "funnel stage (tofu/mofu/bofu) with intent tags and volume estimates — candidates for " +
    "the org's tracked prompt library.",
  geoPromptResearchSchema,
  {
    type: "object",
    properties: {
      topic: { type: "string", description: "Topic or niche to research prompts for" },
      limit: { type: "integer", minimum: 1, maximum: 100, description: "Maximum suggestions to return (default 20)" },
    },
    required: ["topic"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/geo/prompts/research", args)
);

// ---------------------------------------------------------------------------
// geo_prompt_tracker — GET /geo/prompts/tracker
// ---------------------------------------------------------------------------

const geoPromptTrackerSchema = z.object({
  brand: z.string().min(1, "brand is required"),
  competitors: z.array(z.string().min(1)).optional(),
  engines: z.array(engineEnum).optional(),
});

const geoPromptTrackerTool = defineTool(
  "geo_prompt_tracker",
  "Track the brand's rank over time in each answer engine's generated recommendation list " +
    "for every tracked prompt: current/previous/best rank plus a per-day rank history.",
  geoPromptTrackerSchema,
  {
    type: "object",
    properties: {
      brand: { type: "string", description: "Brand name to track ranks for" },
      competitors: {
        type: "array",
        description: "Competitor brand names to include in ranked lists",
        items: { type: "string" },
      },
      engines: enginesJsonSchema,
    },
    required: ["brand"],
    additionalProperties: false,
  },
  (args) =>
    apiClient.get(
      `/geo/prompts/tracker${buildQuery({
        brand: args.brand,
        competitors: args.competitors,
        engines: args.engines,
      })}`
    )
);

// ---------------------------------------------------------------------------
// geo_citations_scan — POST /geo/citations/scan
// ---------------------------------------------------------------------------

const geoCitationsScanSchema = z.object({
  brand: z.string().min(1, "brand is required"),
  prompts: z.array(z.string().min(1)).optional(),
  engines: z.array(engineEnum).optional(),
  own_domain: z.string().optional(),
});

const geoCitationsScanTool = defineTool(
  "geo_citations_scan",
  "Scan which URLs/domains answer engines cite when answering brand-relevant prompts, " +
    "aggregated into per-domain stats with category, trust weight, citation frequency, and " +
    "a priority score for outreach.",
  geoCitationsScanSchema,
  {
    type: "object",
    properties: {
      brand: { type: "string", description: "Brand name the prompts relate to" },
      prompts: promptsJsonSchema,
      engines: enginesJsonSchema,
      own_domain: { type: "string", description: "The brand's own domain (omitted = derived from the brand name)" },
    },
    required: ["brand"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/geo/citations/scan", args)
);

// ---------------------------------------------------------------------------
// geo_domain_trust — GET /geo/citations/domains
// ---------------------------------------------------------------------------

const geoDomainTrustSchema = z.object({
  own_domain: z.string().optional(),
});

const geoDomainTrustTool = defineTool(
  "geo_domain_trust",
  "Get the org-wide aggregated trust analysis of every source domain seen across citation " +
    "scans: category (community, encyclopedia, review platform, ...), trust weight, citation " +
    "counts, and priority score, sorted by priority.",
  geoDomainTrustSchema,
  {
    type: "object",
    properties: {
      own_domain: { type: "string", description: "The brand's own domain, to classify it separately" },
    },
    required: [],
    additionalProperties: false,
  },
  (args) => apiClient.get(`/geo/citations/domains${buildQuery({ own_domain: args.own_domain })}`)
);

// ---------------------------------------------------------------------------
// geo_sentiment_scan — POST /geo/sentiment/scan
// ---------------------------------------------------------------------------

const geoSentimentScanSchema = z.object({
  brand: z.string().min(1, "brand is required"),
  prompts: z.array(z.string().min(1)).optional(),
  engines: z.array(engineEnum).optional(),
});

const geoSentimentScanTool = defineTool(
  "geo_sentiment_scan",
  "Profile how answer engines talk about a brand: an engine x prompt sentiment heatmap " +
    "(positive/neutral/negative with -1..1 scores), per-engine averages, and an overall " +
    "sentiment label.",
  geoSentimentScanSchema,
  {
    type: "object",
    properties: {
      brand: { type: "string", description: "Brand name to profile sentiment for" },
      prompts: promptsJsonSchema,
      engines: enginesJsonSchema,
    },
    required: ["brand"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/geo/sentiment/scan", args)
);

// ---------------------------------------------------------------------------
// geo_ai_readiness_audit — POST /geo/readiness/audit
// ---------------------------------------------------------------------------

const geoAiReadinessAuditSchema = z.object({
  url: z.string().min(1, "url is required"),
});

const geoAiReadinessAuditTool = defineTool(
  "geo_ai_readiness_audit",
  "Audit a site's readiness for AI answer engines: llms.txt, robots.txt access for AI " +
    "crawlers (GPTBot, ClaudeBot, PerplexityBot, ...), structured data, and content signals. " +
    "Returns a weighted 0-100 score, grade, per-check results, and prioritized fixes.",
  geoAiReadinessAuditSchema,
  {
    type: "object",
    properties: {
      url: { type: "string", description: "Absolute URL of the site to audit, e.g. https://example.com" },
    },
    required: ["url"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/geo/readiness/audit", args)
);

// ---------------------------------------------------------------------------

/** All GEO tools exposed by this MCP server. */
export const geoTools: ToolDefinition[] = [
  geoVisibilityScanTool,
  geoPromptResearchTool,
  geoPromptTrackerTool,
  geoCitationsScanTool,
  geoDomainTrustTool,
  geoSentimentScanTool,
  geoAiReadinessAuditTool,
];
