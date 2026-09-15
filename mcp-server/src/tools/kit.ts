/**
 * "Kit" assistant MCP tools.
 *
 * Guided plain-English action plans, the agentic execution queue,
 * keyword-to-page mapping / cannibalization detection, and the content
 * calendar — backed by /api/v1/assistant/* routes.
 */

import { z } from "zod";
import { apiClient } from "../apiClient.js";
import { defineTool, type ToolDefinition } from "./define.js";

/** Executable queue action types (models/assistant.py ActionType). */
const ACTION_TYPES = [
  "write_blog_post",
  "update_meta_tags",
  "publish_gbp_update",
  "sync_directory_listing",
] as const;

/** Content calendar cadences (models/assistant.py CalendarCadence). */
const CADENCES = ["daily", "weekly", "biweekly", "monthly"] as const;

const sitePageSchema = z.object({
  url: z.string().min(1),
  title: z.string().optional(),
  content: z.string().optional(),
});

const sitePageJsonSchema = {
  type: "object",
  properties: {
    url: { type: "string", description: "Page URL" },
    title: { type: "string", description: "Page title" },
    content: { type: "string", description: "Plain-text page content" },
  },
  required: ["url"],
  additionalProperties: false,
} as const;

// ---------------------------------------------------------------------------
// kit_action_plan — POST /assistant/actions/plan
// ---------------------------------------------------------------------------

const issueSchema = z.object({
  code: z.string().min(1),
  title: z.string().min(1),
  description: z.string().optional(),
  category: z.string().optional(),
  severity: z.enum(["critical", "high", "medium", "low", "info"]).optional(),
  recommendation: z.string().optional(),
  url: z.string().optional(),
  details: z.record(z.string(), z.unknown()).optional(),
});

const kitActionPlanSchema = z.object({
  site: z.string().min(1, "site is required"),
  crawl_id: z.string().optional(),
  domain: z.string().optional(),
  country: z.string().optional(),
  issues: z.array(issueSchema).optional(),
});

const kitActionPlanTool = defineTool(
  "kit_action_plan",
  "Build a prioritized, plain-English SEO action plan for a site: each item explains what " +
    "the finding means, why it matters, and numbered no-dev-experience-needed fix steps. " +
    "Sources findings from a stored crawl, ranking data, and/or issues you pass in.",
  kitActionPlanSchema,
  {
    type: "object",
    properties: {
      site: { type: "string", description: "Site identifier or base URL the plan is for" },
      crawl_id: { type: "string", description: "Stored crawl ID to derive findings from" },
      domain: { type: "string", description: "Domain to pull rank-tracking findings for" },
      country: { type: "string", description: "ISO country code for ranking data (default us)" },
      issues: {
        type: "array",
        description: "Audit issues to convert into action items directly",
        items: {
          type: "object",
          properties: {
            code: { type: "string", description: "Machine issue code, e.g. missing_title" },
            title: { type: "string", description: "Human-readable issue title" },
            description: { type: "string" },
            category: { type: "string", description: "Issue category, e.g. technical, on_page, content" },
            severity: { type: "string", enum: ["critical", "high", "medium", "low", "info"] },
            recommendation: { type: "string" },
            url: { type: "string", description: "Affected page URL" },
            details: { type: "object", description: "Analyzer-specific extra details" },
          },
          required: ["code", "title"],
          additionalProperties: false,
        },
      },
    },
    required: ["site"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/assistant/actions/plan", args)
);

// ---------------------------------------------------------------------------
// kit_queue_action — POST /assistant/queue
// ---------------------------------------------------------------------------

const kitQueueActionSchema = z.object({
  type: z.enum(ACTION_TYPES),
  params: z.record(z.string(), z.unknown()).optional(),
  approval_required: z.boolean().optional(),
  max_attempts: z.number().int().min(1).max(10).optional(),
});

const kitQueueActionTool = defineTool(
  "kit_queue_action",
  "Enqueue an agentic action for the org's execution queue (write_blog_post, " +
    "update_meta_tags, publish_gbp_update, sync_directory_listing), optionally gated behind " +
    "human approval. Run the queue afterwards with kit_run_queue.",
  kitQueueActionSchema,
  {
    type: "object",
    properties: {
      type: { type: "string", enum: [...ACTION_TYPES], description: "Type of action to execute" },
      params: {
        type: "object",
        description: "Action parameters (shape depends on type, e.g. { \"keyword\": \"...\" } for write_blog_post)",
      },
      approval_required: { type: "boolean", description: "Require human approval before the action may run (default false)" },
      max_attempts: { type: "integer", minimum: 1, maximum: 10, description: "Max execution attempts (default 3)" },
    },
    required: ["type"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/assistant/queue", args)
);

// ---------------------------------------------------------------------------
// kit_run_queue — POST /assistant/queue/run
// ---------------------------------------------------------------------------

const kitRunQueueSchema = z.object({});

const kitRunQueueTool = defineTool(
  "kit_run_queue",
  "Run one pass of the org's agentic execution queue: executes every pending action " +
    "(skipping those still awaiting approval) and reports completed/failed counts plus " +
    "per-action logs and results. Takes no arguments.",
  kitRunQueueSchema,
  {
    type: "object",
    properties: {},
    required: [],
    additionalProperties: false,
  },
  () => apiClient.post("/assistant/queue/run", {})
);

// ---------------------------------------------------------------------------
// kit_keyword_map — POST /assistant/keywords/map
// ---------------------------------------------------------------------------

const kitKeywordMapSchema = z.object({
  keywords: z.array(z.string().min(1)).min(1, "at least one keyword is required"),
  pages: z.array(sitePageSchema).min(1, "at least one page is required"),
  cannibalization_ratio: z.number().gt(0).max(1).optional(),
});

const kitKeywordMapTool = defineTool(
  "kit_keyword_map",
  "Map each keyword to its most relevant site page (with runner-up alternatives), flag " +
    "keyword cannibalization where multiple pages compete closely, and list unmapped keywords.",
  kitKeywordMapSchema,
  {
    type: "object",
    properties: {
      keywords: { type: "array", description: "Keywords to assign to pages", items: { type: "string" } },
      pages: { type: "array", description: "Candidate site pages (url, title, content)", items: sitePageJsonSchema },
      cannibalization_ratio: {
        type: "number",
        exclusiveMinimum: 0,
        maximum: 1,
        description: "Runner-up/primary score ratio that flags cannibalization (default 0.8)",
      },
    },
    required: ["keywords", "pages"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/assistant/keywords/map", args)
);

// ---------------------------------------------------------------------------
// kit_content_calendar — POST /assistant/calendar/build
// ---------------------------------------------------------------------------

const calendarKeywordSchema = z.object({
  keyword: z.string().min(1),
  search_volume: z.number().int().min(0).optional(),
  difficulty: z.number().int().min(0).max(100).optional(),
  cpc: z.number().min(0).optional(),
  competition: z.number().min(0).max(1).optional(),
  intent: z.enum(["informational", "navigational", "commercial", "transactional"]).optional(),
  parent_topic: z.string().optional(),
});

const kitContentCalendarSchema = z.object({
  keywords: z.array(calendarKeywordSchema).min(1, "at least one keyword is required"),
  start_date: z.string().min(1, "start_date is required"),
  cadence: z.enum(CADENCES).optional(),
  max_entries: z.number().int().min(1).max(100).optional(),
  pages: z.array(sitePageSchema).optional(),
});

const kitContentCalendarTool = defineTool(
  "kit_content_calendar",
  "Build a publish-ready content calendar from keyword data: dated entries at the chosen " +
    "cadence, each with a full article outline (H1/H2s, target + supporting keywords, " +
    "intent, internal links). Pass site pages to get internal links from keyword mapping.",
  kitContentCalendarSchema,
  {
    type: "object",
    properties: {
      keywords: {
        type: "array",
        description: "Keywords (with optional metrics) to plan articles around",
        items: {
          type: "object",
          properties: {
            keyword: { type: "string" },
            search_volume: { type: "integer", minimum: 0 },
            difficulty: { type: "integer", minimum: 0, maximum: 100 },
            cpc: { type: "number", minimum: 0 },
            competition: { type: "number", minimum: 0, maximum: 1 },
            intent: {
              type: "string",
              enum: ["informational", "navigational", "commercial", "transactional"],
            },
            parent_topic: { type: "string" },
          },
          required: ["keyword"],
          additionalProperties: false,
        },
      },
      start_date: { type: "string", description: "ISO-8601 date the calendar starts on, e.g. 2026-08-01" },
      cadence: { type: "string", enum: [...CADENCES], description: "Publishing cadence (default weekly)" },
      max_entries: { type: "integer", minimum: 1, maximum: 100, description: "Maximum calendar entries (default 12)" },
      pages: {
        type: "array",
        description: "Site pages used to derive internal-link suggestions",
        items: sitePageJsonSchema,
      },
    },
    required: ["keywords", "start_date"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/assistant/calendar/build", args)
);

// ---------------------------------------------------------------------------

/** All Kit assistant tools exposed by this MCP server. */
export const kitTools: ToolDefinition[] = [
  kitActionPlanTool,
  kitQueueActionTool,
  kitRunQueueTool,
  kitKeywordMapTool,
  kitContentCalendarTool,
];
