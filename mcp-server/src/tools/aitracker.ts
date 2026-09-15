/**
 * AI Answer-Engine Visibility Tracker MCP tools (v2, PRODUCT_SPEC §8).
 *
 * Scheduled, managed, tier-gated tracking on top of the one-shot GEO scans:
 * org-scoped tracker configs (named prompt sets + market/language +
 * competitors + refresh cadence), on-demand runs, Visibility Score /
 * Share-of-Voice rollups with run-over-run deltas, and the Mention-Gap
 * report — backed by the backend's /api/v1/ai-tracker/* routes. Every route
 * requires the `ai_tracker` plan feature.
 */

import { z } from "zod";
import { apiClient } from "../apiClient.js";
import { buildQuery, defineTool, type ToolDefinition } from "./define.js";

/** Answer engines the v2 tracker queries (models/aitracker.py TrackerEngine). */
const TRACKER_ENGINES = [
  "chatgpt",
  "perplexity",
  "gemini",
  "google_ai_overviews",
  "google_ai_mode",
] as const;

/** Plan-gated refresh cadences (models/aitracker.py RefreshCadence). */
const REFRESH_CADENCES = ["daily", "weekly"] as const;

const trackerEngineEnum = z.enum(TRACKER_ENGINES);
const refreshCadenceEnum = z.enum(REFRESH_CADENCES);

const trackerEnginesJsonSchema = {
  type: "array",
  description: "Answer engines to track (empty/omitted = the plan's full allowed engine set)",
  items: { type: "string", enum: [...TRACKER_ENGINES] },
} as const;

const configIdJsonSchema = {
  type: "string",
  description: "Tracker config ID",
} as const;

const configIdSchema = z.string().min(1, "config_id is required");

function configPath(configId: string, suffix = ""): string {
  return `/ai-tracker/configs/${encodeURIComponent(configId)}${suffix}`;
}

// ---------------------------------------------------------------------------
// tracker_create_config — POST /ai-tracker/configs
// ---------------------------------------------------------------------------

const trackerCreateConfigSchema = z.object({
  name: z.string().min(1, "name is required"),
  brand: z.string().min(1, "brand is required"),
  prompts: z.array(z.string().min(1)).optional(),
  competitors: z.array(z.string().min(1)).optional(),
  engines: z.array(trackerEngineEnum).optional(),
  market: z.string().optional(),
  language: z.string().optional(),
  own_domain: z.string().optional(),
  refresh_cadence: refreshCadenceEnum.optional(),
});

const trackerCreateConfigTool = defineTool(
  "tracker_create_config",
  "Create an AI visibility tracker config: a named prompt set for a brand with target " +
    "market/language, competitors, answer engines, and a daily/weekly refresh cadence " +
    "(plan-gated). Returns the stored config including its ID.",
  trackerCreateConfigSchema,
  {
    type: "object",
    properties: {
      name: { type: "string", description: "Human-readable name for the tracker config" },
      brand: { type: "string", description: "Brand name to track visibility for" },
      prompts: {
        type: "array",
        description: "Prompts to track the brand against",
        items: { type: "string" },
      },
      competitors: {
        type: "array",
        description: "Competitor brand names for share-of-voice comparison",
        items: { type: "string" },
      },
      engines: trackerEnginesJsonSchema,
      market: { type: "string", description: "Target market, e.g. global, US, DE (default global)" },
      language: { type: "string", description: "Prompt language code (default en)" },
      own_domain: { type: "string", description: "The brand's own domain (omitted = derived from the brand name)" },
      refresh_cadence: { type: "string", enum: [...REFRESH_CADENCES], description: "Scheduled refresh cadence (default weekly; plan-gated)" },
    },
    required: ["name", "brand"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/ai-tracker/configs", args)
);

// ---------------------------------------------------------------------------
// tracker_list_configs — GET /ai-tracker/configs
// ---------------------------------------------------------------------------

const trackerListConfigsSchema = z.object({});

const trackerListConfigsTool = defineTool(
  "tracker_list_configs",
  "List all of the organization's AI visibility tracker configs with their prompt sets, " +
    "engines, cadence, and last run time.",
  trackerListConfigsSchema,
  {
    type: "object",
    properties: {},
    required: [],
    additionalProperties: false,
  },
  () => apiClient.get("/ai-tracker/configs")
);

// ---------------------------------------------------------------------------
// tracker_get_config — GET /ai-tracker/configs/{config_id}
// ---------------------------------------------------------------------------

const trackerGetConfigSchema = z.object({
  config_id: configIdSchema,
});

const trackerGetConfigTool = defineTool(
  "tracker_get_config",
  "Get a single AI visibility tracker config by ID: prompts, competitors, engines, " +
    "market/language, own domain, refresh cadence, and last run time.",
  trackerGetConfigSchema,
  {
    type: "object",
    properties: {
      config_id: configIdJsonSchema,
    },
    required: ["config_id"],
    additionalProperties: false,
  },
  (args) => apiClient.get(configPath(args.config_id))
);

// ---------------------------------------------------------------------------
// tracker_update_config — PUT /ai-tracker/configs/{config_id}
// ---------------------------------------------------------------------------

const trackerUpdateConfigSchema = z.object({
  config_id: configIdSchema,
  name: z.string().min(1).optional(),
  brand: z.string().min(1).optional(),
  prompts: z.array(z.string().min(1)).optional(),
  competitors: z.array(z.string().min(1)).optional(),
  engines: z.array(trackerEngineEnum).optional(),
  market: z.string().optional(),
  language: z.string().optional(),
  own_domain: z.string().optional(),
  refresh_cadence: refreshCadenceEnum.optional(),
});

const trackerUpdateConfigTool = defineTool(
  "tracker_update_config",
  "Partially update an AI visibility tracker config: only the supplied fields change " +
    "(an empty engines array resets to the plan default). Returns the updated config.",
  trackerUpdateConfigSchema,
  {
    type: "object",
    properties: {
      config_id: configIdJsonSchema,
      name: { type: "string", description: "New name for the tracker config" },
      brand: { type: "string", description: "New brand name to track" },
      prompts: {
        type: "array",
        description: "Replacement prompt set",
        items: { type: "string" },
      },
      competitors: {
        type: "array",
        description: "Replacement competitor list",
        items: { type: "string" },
      },
      engines: trackerEnginesJsonSchema,
      market: { type: "string", description: "New target market" },
      language: { type: "string", description: "New prompt language code" },
      own_domain: { type: "string", description: "New own domain" },
      refresh_cadence: { type: "string", enum: [...REFRESH_CADENCES], description: "New refresh cadence (plan-gated)" },
    },
    required: ["config_id"],
    additionalProperties: false,
  },
  ({ config_id, ...body }) => apiClient.put(configPath(config_id), body)
);

// ---------------------------------------------------------------------------
// tracker_delete_config — DELETE /ai-tracker/configs/{config_id}
// ---------------------------------------------------------------------------

const trackerDeleteConfigSchema = z.object({
  config_id: configIdSchema,
});

const trackerDeleteConfigTool = defineTool(
  "tracker_delete_config",
  "Delete an AI visibility tracker config (and its stored runs) by ID.",
  trackerDeleteConfigSchema,
  {
    type: "object",
    properties: {
      config_id: configIdJsonSchema,
    },
    required: ["config_id"],
    additionalProperties: false,
  },
  (args) => apiClient.delete(configPath(args.config_id))
);

// ---------------------------------------------------------------------------
// tracker_run — POST /ai-tracker/configs/{config_id}/run
// ---------------------------------------------------------------------------

const trackerRunSchema = z.object({
  config_id: configIdSchema,
  now: z.string().optional(),
});

const trackerRunTool = defineTool(
  "tracker_run",
  "Run an AI visibility tracker config now: query every configured engine with every " +
    "prompt and return the full run report — parsed answers, the Visibility Score / " +
    "Share-of-Voice rollup (with run-over-run deltas), and the Mention-Gap report.",
  trackerRunSchema,
  {
    type: "object",
    properties: {
      config_id: configIdJsonSchema,
      now: { type: "string", description: "Optional ISO-8601 timestamp to record as the run time (defaults to now)" },
    },
    required: ["config_id"],
    additionalProperties: false,
  },
  (args) => apiClient.post(`${configPath(args.config_id, "/run")}${buildQuery({ now: args.now })}`, {})
);

// ---------------------------------------------------------------------------
// tracker_history — GET /ai-tracker/configs/{config_id}/history
// ---------------------------------------------------------------------------

const trackerHistorySchema = z.object({
  config_id: configIdSchema,
});

const trackerHistoryTool = defineTool(
  "tracker_history",
  "Get the run-over-run history of a tracker config: one Visibility Score / Share-of-Voice " +
    "rollup per run, in chronological order, for trend charting.",
  trackerHistorySchema,
  {
    type: "object",
    properties: {
      config_id: configIdJsonSchema,
    },
    required: ["config_id"],
    additionalProperties: false,
  },
  (args) => apiClient.get(configPath(args.config_id, "/history"))
);

// ---------------------------------------------------------------------------
// tracker_visibility — GET /ai-tracker/configs/{config_id}/visibility
// ---------------------------------------------------------------------------

const trackerVisibilitySchema = z.object({
  config_id: configIdSchema,
});

const trackerVisibilityTool = defineTool(
  "tracker_visibility",
  "Get the latest visibility rollup for a tracker config: per-engine and overall mention " +
    "rate, average position, citation share, 0-100 Visibility Score, Share of Voice vs " +
    "competitors, sentiment, and deltas vs the previous run. 404 if the config has no runs yet.",
  trackerVisibilitySchema,
  {
    type: "object",
    properties: {
      config_id: configIdJsonSchema,
    },
    required: ["config_id"],
    additionalProperties: false,
  },
  (args) => apiClient.get(configPath(args.config_id, "/visibility"))
);

// ---------------------------------------------------------------------------
// tracker_mention_gap — GET /ai-tracker/configs/{config_id}/mention-gap
// ---------------------------------------------------------------------------

const trackerMentionGapSchema = z.object({
  config_id: configIdSchema,
});

const trackerMentionGapTool = defineTool(
  "tracker_mention_gap",
  "Get the latest Mention-Gap report for a tracker config: prompts where competitors are " +
    "mentioned but the brand is not, with the gap engines and an opportunity score per " +
    "prompt, ranked by opportunity. 404 if the config has no runs yet.",
  trackerMentionGapSchema,
  {
    type: "object",
    properties: {
      config_id: configIdJsonSchema,
    },
    required: ["config_id"],
    additionalProperties: false,
  },
  (args) => apiClient.get(configPath(args.config_id, "/mention-gap"))
);

// ---------------------------------------------------------------------------
// tracker_due — GET /ai-tracker/due
// ---------------------------------------------------------------------------

const trackerDueSchema = z.object({
  now: z.string().optional(),
});

const trackerDueTool = defineTool(
  "tracker_due",
  "Ops endpoint (admin/owner only): list the org's tracker configs due for a scheduled " +
    "refresh based on their cadence and last run time — then trigger each with tracker_run.",
  trackerDueSchema,
  {
    type: "object",
    properties: {
      now: { type: "string", description: "Optional ISO-8601 timestamp to evaluate due-ness against (defaults to now)" },
    },
    required: [],
    additionalProperties: false,
  },
  (args) => apiClient.get(`/ai-tracker/due${buildQuery({ now: args.now })}`)
);

// ---------------------------------------------------------------------------

/** All AI Answer-Engine Visibility Tracker tools exposed by this MCP server. */
export const aitrackerTools: ToolDefinition[] = [
  trackerCreateConfigTool,
  trackerListConfigsTool,
  trackerGetConfigTool,
  trackerUpdateConfigTool,
  trackerDeleteConfigTool,
  trackerRunTool,
  trackerHistoryTool,
  trackerVisibilityTool,
  trackerMentionGapTool,
  trackerDueTool,
];
