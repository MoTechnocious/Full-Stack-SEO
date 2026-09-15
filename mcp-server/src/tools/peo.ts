/**
 * PEO (Personal Entity Optimization) MCP tools.
 *
 * Knowledge Graph entity search/tracking, the KG confidence sensor,
 * NLP-optimized entity bio building, cross-source corroboration audits, and
 * Person/Organization JSON-LD schema — backed by /api/v1/peo/* routes.
 */

import { z } from "zod";
import { apiClient } from "../apiClient.js";
import { buildQuery, defineTool, type ToolDefinition } from "./define.js";

/** Corroboration source profiles the backend understands (models/peo.py SourceType). */
const SOURCE_TYPES = ["wikipedia", "wikidata", "crunchbase", "linkedin", "own_site"] as const;

const sourceTypeEnum = z.enum(SOURCE_TYPES);

// ---------------------------------------------------------------------------
// peo_entity_search — POST /peo/entities/search
// ---------------------------------------------------------------------------

const peoEntitySearchSchema = z.object({
  query: z.string().min(1, "query is required"),
  types: z.array(z.string().min(1)).optional(),
  limit: z.number().int().min(1).max(50).optional(),
});

const peoEntitySearchTool = defineTool(
  "peo_entity_search",
  "Search the Google Knowledge Graph for entity candidates matching a name/query, " +
    "returning KGMIDs, schema.org types, descriptions, and result scores.",
  peoEntitySearchSchema,
  {
    type: "object",
    properties: {
      query: { type: "string", description: "Entity name or query to search the Knowledge Graph for" },
      types: {
        type: "array",
        description: "Optional schema.org type filter, e.g. [\"Person\"]",
        items: { type: "string" },
      },
      limit: { type: "integer", minimum: 1, maximum: 50, description: "Maximum entities to return (default 10)" },
    },
    required: ["query"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/peo/entities/search", args)
);

// ---------------------------------------------------------------------------
// peo_entity_track — POST /peo/entities/track
// ---------------------------------------------------------------------------

const peoEntityTrackSchema = z.object({
  kg_mid: z.string().min(1, "kg_mid is required"),
  name: z.string().min(1, "name is required"),
  types: z.array(z.string().min(1)).optional(),
  description: z.string().optional(),
});

const peoEntityTrackTool = defineTool(
  "peo_entity_track",
  "Register a Knowledge Graph entity (by KGMID) for org-scoped tracking, so the KG sensor " +
    "can monitor its confidence score over time.",
  peoEntityTrackSchema,
  {
    type: "object",
    properties: {
      kg_mid: { type: "string", description: "Knowledge Graph machine ID, e.g. /g/1a2b3c4d5e" },
      name: { type: "string", description: "Entity display name" },
      types: {
        type: "array",
        description: "schema.org types of the entity, e.g. [\"Person\"]",
        items: { type: "string" },
      },
      description: { type: "string", description: "Short entity description" },
    },
    required: ["kg_mid", "name"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/peo/entities/track", args)
);

// ---------------------------------------------------------------------------
// peo_entity_sensor — GET /peo/entities/sensor
// ---------------------------------------------------------------------------

const peoEntitySensorSchema = z.object({
  kg_mid: z.string().min(1, "kg_mid is required"),
  points: z.number().int().min(2).max(52).optional(),
});

const peoEntitySensorTool = defineTool(
  "peo_entity_sensor",
  "Read the Knowledge Graph sensor for a tracked entity: its confidence-score time series " +
    "plus latest/mean score, net change, volatility, and a trend classification " +
    "(rising/stable/volatile/declining).",
  peoEntitySensorSchema,
  {
    type: "object",
    properties: {
      kg_mid: { type: "string", description: "Tracked entity KGMID, e.g. /g/1a2b3c4d5e" },
      points: { type: "integer", minimum: 2, maximum: 52, description: "Number of series points to return (default 12)" },
    },
    required: ["kg_mid"],
    additionalProperties: false,
  },
  (args) =>
    apiClient.get(`/peo/entities/sensor${buildQuery({ kg_mid: args.kg_mid, points: args.points })}`)
);

// ---------------------------------------------------------------------------
// peo_build_bio — POST /peo/bio/build
// ---------------------------------------------------------------------------

const peoBuildBioSchema = z.object({
  name: z.string().min(1, "name is required"),
  roles: z.array(z.string().min(1)).optional(),
  organizations: z.array(z.string().min(1)).optional(),
  works: z.array(z.string().min(1)).optional(),
  credentials: z.array(z.string().min(1)).optional(),
  location: z.string().optional(),
  websites: z.array(z.string().min(1)).optional(),
});

const peoBuildBioTool = defineTool(
  "peo_build_bio",
  "Assemble NLP-optimized entity bio variants (short/medium/long) from structured facts, " +
    "maximizing subject-predicate-object triple density so knowledge graphs and LLMs can " +
    "extract facts reliably.",
  peoBuildBioSchema,
  {
    type: "object",
    properties: {
      name: { type: "string", description: "Entity (person/brand) name the bio is about" },
      roles: { type: "array", description: "Roles/titles, e.g. [\"CEO\", \"angel investor\"]", items: { type: "string" } },
      organizations: {
        type: "array",
        description: "Affiliated organizations (first = primary affiliation)",
        items: { type: "string" },
      },
      works: { type: "array", description: "Books, products, notable projects", items: { type: "string" } },
      credentials: { type: "array", description: "Degrees, awards, certifications", items: { type: "string" } },
      location: { type: "string", description: "Home base, e.g. \"Austin, Texas\"" },
      websites: { type: "array", description: "Official website / profile URLs", items: { type: "string" } },
    },
    required: ["name"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/peo/bio/build", args)
);

// ---------------------------------------------------------------------------
// peo_corroboration_audit — POST /peo/corroboration/audit
// ---------------------------------------------------------------------------

const sourceProfileSchema = z.object({
  source: sourceTypeEnum,
  url: z.string().optional(),
  facts: z.record(z.string(), z.string()),
});

const peoCorroborationAuditSchema = z.object({
  entity_name: z.string().min(1, "entity_name is required"),
  canonical_facts: z.record(z.string(), z.string()),
  profiles: z.array(sourceProfileSchema).optional(),
  fetch_sources: z.array(sourceTypeEnum).optional(),
});

const sourceProfileJsonSchema = {
  type: "object",
  properties: {
    source: { type: "string", enum: [...SOURCE_TYPES], description: "Which profile the facts came from" },
    url: { type: "string", description: "URL of the profile page" },
    facts: { type: "object", description: "Fact name -> value as asserted by this profile" },
  },
  required: ["source", "facts"],
  additionalProperties: false,
} as const;

const peoCorroborationAuditTool = defineTool(
  "peo_corroboration_audit",
  "Audit cross-source consistency of an entity's key facts: diff a canonical narrative " +
    "against Wikipedia/Wikidata/Crunchbase/LinkedIn/own-site profiles, returning a 0-100 " +
    "consistency score, per-fact match/mismatch/missing status, and suggested fixes.",
  peoCorroborationAuditSchema,
  {
    type: "object",
    properties: {
      entity_name: { type: "string", description: "Entity the facts describe" },
      canonical_facts: {
        type: "object",
        description: "Canonical fact name -> value pairs, e.g. { \"employer\": \"Acme Inc\" }",
      },
      profiles: {
        type: "array",
        description: "Source profiles (with their asserted facts) to diff against",
        items: sourceProfileJsonSchema,
      },
      fetch_sources: {
        type: "array",
        description: "Sources the backend should fetch profiles from itself",
        items: { type: "string", enum: [...SOURCE_TYPES] },
      },
    },
    required: ["entity_name", "canonical_facts"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/peo/corroboration/audit", args)
);

// ---------------------------------------------------------------------------
// peo_entity_schema — POST /peo/schema/entity
// ---------------------------------------------------------------------------

const peoEntitySchemaSchema = z.object({
  entity_type: z.enum(["Person", "Organization"]),
  name: z.string().min(1, "name is required"),
  url: z.string().optional(),
  description: z.string().optional(),
  same_as: z.array(z.string().min(1)).optional(),
  image: z.string().optional(),
  job_title: z.string().optional(),
  works_for: z.string().optional(),
  founder_of: z.array(z.string().min(1)).optional(),
  author_of: z.array(z.string().min(1)).optional(),
  alumni_of: z.array(z.string().min(1)).optional(),
  logo: z.string().optional(),
  founding_date: z.string().optional(),
  founders: z.array(z.string().min(1)).optional(),
});

const peoEntitySchemaTool = defineTool(
  "peo_entity_schema",
  "Generate a relationally-linked Person or Organization JSON-LD block (with sameAs " +
    "corroboration URLs, worksFor/founder/author/alumniOf relations) plus a ready-to-paste " +
    "<script> tag.",
  peoEntitySchemaSchema,
  {
    type: "object",
    properties: {
      entity_type: { type: "string", enum: ["Person", "Organization"], description: "schema.org entity type to emit" },
      name: { type: "string", description: "Entity name" },
      url: { type: "string", description: "Canonical URL of the entity" },
      description: { type: "string", description: "Short entity description" },
      same_as: { type: "array", description: "Corroborating profile URLs (emitted as sameAs)", items: { type: "string" } },
      image: { type: "string", description: "Image URL for the entity" },
      job_title: { type: "string", description: "Person: current job title" },
      works_for: { type: "string", description: "Person: employing organization" },
      founder_of: { type: "array", description: "Person: organizations founded", items: { type: "string" } },
      author_of: { type: "array", description: "Person: creative works authored", items: { type: "string" } },
      alumni_of: { type: "array", description: "Person: schools/universities attended", items: { type: "string" } },
      logo: { type: "string", description: "Organization: logo URL" },
      founding_date: { type: "string", description: "Organization: founding date (ISO-8601)" },
      founders: { type: "array", description: "Organization: founder names", items: { type: "string" } },
    },
    required: ["entity_type", "name"],
    additionalProperties: false,
  },
  (args) => apiClient.post("/peo/schema/entity", args)
);

// ---------------------------------------------------------------------------

/** All PEO tools exposed by this MCP server. */
export const peoTools: ToolDefinition[] = [
  peoEntitySearchTool,
  peoEntityTrackTool,
  peoEntitySensorTool,
  peoBuildBioTool,
  peoCorroborationAuditTool,
  peoEntitySchemaTool,
];
