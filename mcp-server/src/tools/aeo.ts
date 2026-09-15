/**
 * AEO (Answer Engine Optimization) MCP tools.
 *
 * People-Also-Ask question extraction, question clustering / FAQ mapping,
 * combined JSON-LD schema graphs, internal-link suggestions, and voice-search
 * readiness audits — backed by /api/v1/aeo/* routes.
 */

import { z } from "zod";
import { apiClient } from "../apiClient.js";
import { defineTool, type ToolDefinition } from "./define.js";

// ---------------------------------------------------------------------------
// aeo_extract_questions — POST /aeo/questions/extract
// ---------------------------------------------------------------------------

const aeoExtractQuestionsSchema = z.object({
  seed: z.string().min(1, "seed is required"),
  depth: z.number().int().min(1).max(3).optional(),
  per_level: z.number().int().min(1).max(10).optional(),
  include_autocomplete: z.boolean().optional(),
  autocomplete_limit: z.number().int().min(1).max(25).optional(),
});

const aeoExtractQuestionsTool = defineTool(
  "aeo_extract_questions",
  "Extract People-Also-Ask style questions for a seed topic, expanding follow-up chains to " +
    "a chosen depth, plus search autocomplete pathways.",
  aeoExtractQuestionsSchema,
  {
    type: "object",
    properties: {
      seed: { type: "string", description: "Seed keyword/topic to extract questions for" },
      depth: { type: "integer", minimum: 1, maximum: 3, description: "Follow-up chain depth (default 2)" },
      per_level: { type: "integer", minimum: 1, maximum: 10, description: "Questions per expansion level (default 4)" },
      include_autocomplete: { type: "boolean", description: "Also return autocomplete pathways (default true)" },
      autocomplete_limit: { type: "integer", minimum: 1, maximum: 25, description: "Max autocomplete suggestions (default 10)" },
    },
    required: ["seed"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/aeo/questions/extract", args)
);

// ---------------------------------------------------------------------------
// aeo_map_clusters — POST /aeo/clusters/map
// ---------------------------------------------------------------------------

const pageRefSchema = z.object({
  url: z.string().min(1),
  title: z.string().optional(),
});

const aeoMapClustersSchema = z.object({
  questions: z.array(z.string().min(1)).min(1, "at least one question is required"),
  pages: z.array(pageRefSchema).optional(),
  similarity_threshold: z.number().min(0).max(1).optional(),
});

const aeoMapClustersTool = defineTool(
  "aeo_map_clusters",
  "Cluster related questions into topic groups and map them to target pages as FAQ entries " +
    "with answer templates — the bridge from PAA research to on-page FAQ content.",
  aeoMapClustersSchema,
  {
    type: "object",
    properties: {
      questions: {
        type: "array",
        description: "Questions to cluster (e.g. from aeo_extract_questions)",
        items: { type: "string" },
      },
      pages: {
        type: "array",
        description: "Candidate target pages for FAQ mapping",
        items: {
          type: "object",
          properties: {
            url: { type: "string", description: "Page URL" },
            title: { type: "string", description: "Page title" },
          },
          required: ["url"],
          additionalProperties: false,
        },
      },
      similarity_threshold: {
        type: "number",
        minimum: 0,
        maximum: 1,
        description: "Minimum similarity for cluster membership (default 0.25)",
      },
    },
    required: ["questions"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/aeo/clusters/map", args)
);

// ---------------------------------------------------------------------------
// aeo_schema_graph — POST /aeo/schema/graph
// ---------------------------------------------------------------------------

const qaItemSchema = z.object({
  question: z.string().min(1),
  answer: z.string().min(1),
});

const qaItemJsonSchema = {
  type: "object",
  properties: {
    question: { type: "string" },
    answer: { type: "string" },
  },
  required: ["question", "answer"],
  additionalProperties: false,
} as const;

const aeoSchemaGraphSchema = z.object({
  url: z.string().min(1, "url is required"),
  title: z.string().min(1, "title is required"),
  description: z.string().optional(),
  breadcrumbs: z
    .array(z.object({ name: z.string().min(1), url: z.string().min(1) }))
    .optional(),
  faqs: z.array(qaItemSchema).optional(),
  qa: qaItemSchema.optional(),
  how_to: z
    .object({
      name: z.string().min(1),
      steps: z.array(z.object({ name: z.string().min(1), text: z.string().optional() })).optional(),
    })
    .optional(),
});

const aeoSchemaGraphTool = defineTool(
  "aeo_schema_graph",
  "Assemble a combined JSON-LD @graph block for a page (WebPage + BreadcrumbList + FAQPage " +
    "+ QAPage + HowTo as supplied), returning the JSON-LD, a ready-to-paste <script> tag, " +
    "and the node types emitted.",
  aeoSchemaGraphSchema,
  {
    type: "object",
    properties: {
      url: { type: "string", description: "Canonical URL of the page" },
      title: { type: "string", description: "Page title" },
      description: { type: "string", description: "Page description" },
      breadcrumbs: {
        type: "array",
        description: "Breadcrumb trail, root first",
        items: {
          type: "object",
          properties: {
            name: { type: "string" },
            url: { type: "string" },
          },
          required: ["name", "url"],
          additionalProperties: false,
        },
      },
      faqs: { type: "array", description: "FAQ question/answer pairs (emits an FAQPage node)", items: qaItemJsonSchema },
      qa: { ...qaItemJsonSchema, description: "Single Q&A (emits a QAPage node)" },
      how_to: {
        type: "object",
        description: "How-to task and its steps (emits a HowTo node)",
        properties: {
          name: { type: "string", description: "Name of the how-to task" },
          steps: {
            type: "array",
            items: {
              type: "object",
              properties: {
                name: { type: "string" },
                text: { type: "string" },
              },
              required: ["name"],
              additionalProperties: false,
            },
          },
        },
        required: ["name"],
        additionalProperties: false,
      },
    },
    required: ["url", "title"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/aeo/schema/graph", args)
);

// ---------------------------------------------------------------------------
// aeo_internal_links — POST /aeo/linking/suggest
// ---------------------------------------------------------------------------

const pageDocSchema = z.object({
  url: z.string().min(1),
  title: z.string().optional(),
  body: z.string().optional(),
  existing_links: z.array(z.string()).optional(),
});

const aeoInternalLinksSchema = z.object({
  pages: z.array(pageDocSchema).min(1, "at least one page is required"),
  similarity_threshold: z.number().min(0).max(1).optional(),
  max_per_page: z.number().int().min(1).max(20).optional(),
});

const aeoInternalLinksTool = defineTool(
  "aeo_internal_links",
  "Suggest internal links between a set of pages based on content similarity, skipping " +
    "links that already exist, with anchor-text suggestions per link.",
  aeoInternalLinksSchema,
  {
    type: "object",
    properties: {
      pages: {
        type: "array",
        description: "Site pages (url, title, body text, existing outbound internal links)",
        items: {
          type: "object",
          properties: {
            url: { type: "string", description: "Page URL" },
            title: { type: "string", description: "Page title" },
            body: { type: "string", description: "Plain-text body content" },
            existing_links: {
              type: "array",
              description: "Outbound internal links already on the page",
              items: { type: "string" },
            },
          },
          required: ["url"],
          additionalProperties: false,
        },
      },
      similarity_threshold: {
        type: "number",
        minimum: 0,
        maximum: 1,
        description: "Minimum similarity to suggest a link (default 0.2)",
      },
      max_per_page: { type: "integer", minimum: 1, maximum: 20, description: "Max suggestions per source page (default 5)" },
    },
    required: ["pages"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/aeo/linking/suggest", args)
);

// ---------------------------------------------------------------------------
// aeo_voice_audit — POST /aeo/voice/audit
// ---------------------------------------------------------------------------

const aeoVoiceAuditSchema = z.object({
  content: z.string().min(1, "content is required"),
  question: z.string().optional(),
  answer_word_limit: z.number().int().min(10).max(200).optional(),
});

const aeoVoiceAuditTool = defineTool(
  "aeo_voice_audit",
  "Audit content for voice-search readiness: Flesch readability, sentence length, syllable " +
    "density, and whether the opening paragraph answers the spoken question concisely. " +
    "Returns a 0-100 score, grade, per-check results, and fixes.",
  aeoVoiceAuditSchema,
  {
    type: "object",
    properties: {
      content: { type: "string", description: "Plain-text content to audit" },
      question: { type: "string", description: "Spoken query the content should answer" },
      answer_word_limit: {
        type: "integer",
        minimum: 10,
        maximum: 200,
        description: "Max words a voice-friendly answer should need (default 50)",
      },
    },
    required: ["content"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/aeo/voice/audit", args)
);

// ---------------------------------------------------------------------------

/** All AEO tools exposed by this MCP server. */
export const aeoTools: ToolDefinition[] = [
  aeoExtractQuestionsTool,
  aeoMapClustersTool,
  aeoSchemaGraphTool,
  aeoInternalLinksTool,
  aeoVoiceAuditTool,
];
