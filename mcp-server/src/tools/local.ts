/**
 * Local SEO MCP tools.
 *
 * Google Business Profile management (posts, metrics, reviews + replies) and
 * citation/NAP distribution across directories — backed by /api/v1/local/*.
 */

import { z } from "zod";
import { apiClient } from "../apiClient.js";
import { buildQuery, defineTool, type ToolDefinition } from "./define.js";

/** Directories the citation sync engine can push to (models/local.py Directory). */
const DIRECTORIES = ["yelp", "apple_maps", "bing_places", "foursquare"] as const;

// ---------------------------------------------------------------------------
// local_gbp_post — POST /local/gbp/posts
// ---------------------------------------------------------------------------

const localGbpPostSchema = z.object({
  summary: z.string().min(1, "summary is required"),
  topic: z.enum(["update", "offer", "event"]).optional(),
  cta_url: z.string().optional(),
});

const localGbpPostTool = defineTool(
  "local_gbp_post",
  "Publish a Google Business Profile post/update (update, offer, or event) with an " +
    "optional call-to-action URL.",
  localGbpPostSchema,
  {
    type: "object",
    properties: {
      summary: { type: "string", description: "Post body text shown on the profile" },
      topic: { type: "string", enum: ["update", "offer", "event"], description: "Post type (default update)" },
      cta_url: { type: "string", description: "Call-to-action URL attached to the post" },
    },
    required: ["summary"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/local/gbp/posts", args)
);

// ---------------------------------------------------------------------------
// local_gbp_metrics — GET /local/gbp/metrics
// ---------------------------------------------------------------------------

const localGbpMetricsSchema = z.object({
  period_days: z.number().int().min(1).max(365).optional(),
});

const localGbpMetricsTool = defineTool(
  "local_gbp_metrics",
  "Get Google Business Profile performance metrics for the org over a period: search/maps " +
    "views, direct vs discovery searches, and customer actions (website clicks, calls, " +
    "direction requests).",
  localGbpMetricsSchema,
  {
    type: "object",
    properties: {
      period_days: { type: "integer", minimum: 1, maximum: 365, description: "Reporting period in days (default 30)" },
    },
    required: [],
    additionalProperties: false,
  },
  (args) => apiClient.get(`/local/gbp/metrics${buildQuery({ period_days: args.period_days })}`)
);

// ---------------------------------------------------------------------------
// local_gbp_reviews — GET /local/gbp/reviews
// ---------------------------------------------------------------------------

const localGbpReviewsSchema = z.object({});

const localGbpReviewsTool = defineTool(
  "local_gbp_reviews",
  "List the org's Google Business Profile reviews (author, rating, text, existing reply) " +
    "together with generated sentiment-aware suggested replies for each review. Takes no " +
    "arguments.",
  localGbpReviewsSchema,
  {
    type: "object",
    properties: {},
    required: [],
    additionalProperties: false,
  },
  () => apiClient.get("/local/gbp/reviews")
);

// ---------------------------------------------------------------------------
// local_reply_review — POST /local/gbp/reviews/{review_id}/reply
// ---------------------------------------------------------------------------

const localReplyReviewSchema = z.object({
  review_id: z.string().min(1, "review_id is required"),
  text: z.string().optional(),
});

const localReplyReviewTool = defineTool(
  "local_reply_review",
  "Reply to a Google Business Profile review. Omit 'text' to publish the backend's " +
    "generated sentiment-aware suggested reply for that review.",
  localReplyReviewSchema,
  {
    type: "object",
    properties: {
      review_id: { type: "string", description: "ID of the review to reply to (see local_gbp_reviews)" },
      text: { type: "string", description: "Reply text; omitted = use the generated suggested reply" },
    },
    required: ["review_id"],
    additionalProperties: false,
  },
  (args) =>
    apiClient.post(`/local/gbp/reviews/${encodeURIComponent(args.review_id)}/reply`, {
      text: args.text,
    })
);

// ---------------------------------------------------------------------------
// local_citation_sync — POST /local/citations/sync
// ---------------------------------------------------------------------------

const localCitationSyncSchema = z.object({
  directory: z.enum(DIRECTORIES).optional(),
});

const localCitationSyncTool = defineTool(
  "local_citation_sync",
  "Push the org's canonical NAP (name/address/phone) record to business directories " +
    "(Yelp, Apple Maps, Bing Places, Foursquare) — all of them, or a single one. Returns " +
    "per-directory delivery state (created/updated/in_sync/failed) and field-level diffs.",
  localCitationSyncSchema,
  {
    type: "object",
    properties: {
      directory: {
        type: "string",
        enum: [...DIRECTORIES],
        description: "Sync only this directory (omitted = all directories)",
      },
    },
    required: [],
    additionalProperties: false,
  },
  (args) => apiClient.post(`/local/citations/sync${buildQuery({ directory: args.directory })}`, {})
);

// ---------------------------------------------------------------------------
// local_citation_status — GET /local/citations/status
// ---------------------------------------------------------------------------

const localCitationStatusSchema = z.object({});

const localCitationStatusTool = defineTool(
  "local_citation_status",
  "Check the org's citation health across directories: whether each directory lists the " +
    "business, NAP drift detection with field-level diffs, and lock state. Takes no arguments.",
  localCitationStatusSchema,
  {
    type: "object",
    properties: {},
    required: [],
    additionalProperties: false,
  },
  () => apiClient.get("/local/citations/status")
);

// ---------------------------------------------------------------------------

/** All Local SEO tools exposed by this MCP server. */
export const localTools: ToolDefinition[] = [
  localGbpPostTool,
  localGbpMetricsTool,
  localGbpReviewsTool,
  localReplyReviewTool,
  localCitationSyncTool,
  localCitationStatusTool,
];
