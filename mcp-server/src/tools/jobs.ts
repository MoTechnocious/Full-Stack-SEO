/**
 * Background job MCP tools.
 *
 * Submit long-running work (crawls, rank polls, report builds) to the backend
 * job queue, then list, poll, and cancel jobs — backed by the backend's
 * /api/v1/jobs/* routes. Quota is enforced at submission time; a succeeded
 * job's `result_ref` points at the produced artifact (crawl_id for crawls,
 * `domain|country` for rank polls, report_id for reports).
 */

import { z } from "zod";
import { apiClient } from "../apiClient.js";
import { buildQuery, defineTool, type ToolDefinition } from "./define.js";

/** Job lifecycle states (models/jobs.py JobStatus). */
const JOB_STATUSES = ["queued", "running", "succeeded", "failed", "cancelled"] as const;

/** Kinds of long-running work executed on the job queue (models/jobs.py JobType). */
const JOB_TYPES = ["crawl", "rank_poll", "report"] as const;

/** Devices a rank poll can simulate (models/common.py Device). */
const DEVICES = ["desktop", "mobile"] as const;

// ---------------------------------------------------------------------------
// jobs_submit_crawl — POST /jobs/crawl
// ---------------------------------------------------------------------------

const jobsSubmitCrawlSchema = z.object({
  start_url: z.string().min(1, "start_url is required"),
  max_pages: z.number().int().min(1).max(100_000).optional(),
  max_depth: z.number().int().min(0).max(50).optional(),
  respect_robots: z.boolean().optional(),
  follow_external: z.boolean().optional(),
  render_js: z.boolean().optional(),
  user_agent: z.string().optional(),
  include_patterns: z.array(z.string()).optional(),
  exclude_patterns: z.array(z.string()).optional(),
});

const jobsSubmitCrawlTool = defineTool(
  "jobs_submit_crawl",
  "Submit a site crawl + SEO audit as a background job instead of running it synchronously " +
    "(same config and quota as run_audit). Returns { job_id, status } immediately; poll with " +
    "jobs_status — the succeeded job's result_ref is the crawl_id of the produced audit.",
  jobsSubmitCrawlSchema,
  {
    type: "object",
    properties: {
      start_url: { type: "string", description: "Absolute URL to start crawling from, e.g. https://example.com" },
      max_pages: { type: "integer", minimum: 1, maximum: 100000, description: "Maximum number of pages to crawl (default 100; capped by plan)" },
      max_depth: { type: "integer", minimum: 0, maximum: 50, description: "Maximum link depth to follow from the start URL (default 5)" },
      respect_robots: { type: "boolean", description: "Honor robots.txt disallow rules (default true)" },
      follow_external: { type: "boolean", description: "Follow links to external domains (default false)" },
      render_js: { type: "boolean", description: "Request JavaScript rendering for crawled pages (default false)" },
      user_agent: { type: "string", description: "User-Agent header the crawler sends" },
      include_patterns: {
        type: "array",
        description: "Only crawl URLs matching one of these patterns",
        items: { type: "string" },
      },
      exclude_patterns: {
        type: "array",
        description: "Skip URLs matching one of these patterns",
        items: { type: "string" },
      },
    },
    required: ["start_url"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/jobs/crawl", args)
);

// ---------------------------------------------------------------------------
// jobs_submit_rank_poll — POST /jobs/rank-poll
// ---------------------------------------------------------------------------

const jobsSubmitRankPollSchema = z.object({
  domain: z.string().min(1, "domain is required"),
  keywords: z.array(z.string().min(1)).min(1, "at least one keyword is required"),
  country: z.string().optional(),
  device: z.enum(DEVICES).optional(),
  search_volumes: z.record(z.string(), z.number().int()).optional(),
});

const jobsSubmitRankPollTool = defineTool(
  "jobs_submit_rank_poll",
  "Submit a keyword rank poll for a domain as a background job (same inputs and quota as " +
    "track_rankings). Returns { job_id, status }; the succeeded job's result_ref is " +
    "'domain|country' for fetching rankings through the existing endpoints.",
  jobsSubmitRankPollSchema,
  {
    type: "object",
    properties: {
      domain: { type: "string", description: "Domain to poll rankings for, e.g. example.com" },
      keywords: {
        type: "array",
        description: "Keywords to poll rankings for",
        items: { type: "string" },
      },
      country: { type: "string", description: "ISO country code to scope the poll to (default us)" },
      device: { type: "string", enum: [...DEVICES], description: "Device to simulate (default desktop)" },
      search_volumes: {
        type: "object",
        description: "Optional keyword -> monthly search volume map for reporting",
      },
    },
    required: ["domain", "keywords"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/jobs/rank-poll", args)
);

// ---------------------------------------------------------------------------
// jobs_submit_report — POST /jobs/report
// ---------------------------------------------------------------------------

const jobsSubmitReportSchema = z.object({
  site: z.string().min(1, "site is required"),
  period_start: z.string().min(1, "period_start is required"),
  period_end: z.string().min(1, "period_end is required"),
  branding: z.record(z.string(), z.unknown()).optional(),
  crawl_id: z.string().optional(),
  domain: z.string().optional(),
  country: z.string().optional(),
});

const jobsSubmitReportTool = defineTool(
  "jobs_submit_report",
  "Submit an SEO report build as a background job (same inputs and quota as generate_report). " +
    "Returns { job_id, status }; the succeeded job's result_ref is the report_id of the built " +
    "report. White-label branding is applied only when the plan includes it.",
  jobsSubmitReportSchema,
  {
    type: "object",
    properties: {
      site: { type: "string", description: "Site identifier or base URL the report is for" },
      period_start: { type: "string", description: "ISO-8601 start date of the report period" },
      period_end: { type: "string", description: "ISO-8601 end date of the report period" },
      branding: {
        type: "object",
        description: "White-label branding overrides (requires the white_label plan feature)",
      },
      crawl_id: { type: "string", description: "Optional crawl ID to scope the report to a specific audit run" },
      domain: { type: "string", description: "Optional domain to scope ranking/report data to" },
      country: { type: "string", description: "ISO country code for ranking data (default us)" },
    },
    required: ["site", "period_start", "period_end"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/jobs/report", args)
);

// ---------------------------------------------------------------------------
// jobs_list — GET /jobs
// ---------------------------------------------------------------------------

const jobsListSchema = z.object({
  status: z.enum(JOB_STATUSES).optional(),
  type: z.enum(JOB_TYPES).optional(),
});

const jobsListTool = defineTool(
  "jobs_list",
  "List the organization's background jobs, optionally filtered by status " +
    "(queued/running/succeeded/failed/cancelled) and/or type (crawl/rank_poll/report), " +
    "with progress, timestamps, result_ref, and error for each.",
  jobsListSchema,
  {
    type: "object",
    properties: {
      status: { type: "string", enum: [...JOB_STATUSES], description: "Only jobs in this lifecycle state" },
      type: { type: "string", enum: [...JOB_TYPES], description: "Only jobs of this type" },
    },
    required: [],
    additionalProperties: false,
  },
  (args) => apiClient.get(`/jobs${buildQuery({ status: args.status, type: args.type })}`)
);

// ---------------------------------------------------------------------------
// jobs_status — GET /jobs/{job_id}
// ---------------------------------------------------------------------------

const jobsStatusSchema = z.object({
  job_id: z.string().min(1, "job_id is required"),
});

const jobsStatusTool = defineTool(
  "jobs_status",
  "Get a single background job by ID: status, 0-100 progress, submitted/started/finished " +
    "timestamps, attempts, error (if failed), and result_ref (once succeeded).",
  jobsStatusSchema,
  {
    type: "object",
    properties: {
      job_id: { type: "string", description: "Job ID returned by a jobs_submit_* tool" },
    },
    required: ["job_id"],
    additionalProperties: false,
  },
  (args) => apiClient.get(`/jobs/${encodeURIComponent(args.job_id)}`)
);

// ---------------------------------------------------------------------------
// jobs_cancel — POST /jobs/{job_id}/cancel
// ---------------------------------------------------------------------------

const jobsCancelSchema = z.object({
  job_id: z.string().min(1, "job_id is required"),
});

const jobsCancelTool = defineTool(
  "jobs_cancel",
  "Cancel a queued or running background job by ID. Returns the updated job; jobs already " +
    "in a terminal state (succeeded/failed/cancelled) are returned unchanged.",
  jobsCancelSchema,
  {
    type: "object",
    properties: {
      job_id: { type: "string", description: "Job ID returned by a jobs_submit_* tool" },
    },
    required: ["job_id"],
    additionalProperties: false,
  },
  (args) => apiClient.post(`/jobs/${encodeURIComponent(args.job_id)}/cancel`, {})
);

// ---------------------------------------------------------------------------

/** All background job tools exposed by this MCP server. */
export const jobsTools: ToolDefinition[] = [
  jobsSubmitCrawlTool,
  jobsSubmitRankPollTool,
  jobsSubmitReportTool,
  jobsListTool,
  jobsStatusTool,
  jobsCancelTool,
];
