/**
 * Shared plumbing for MySEOapp MCP tool definitions.
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
 */

import { z } from "zod";
import type { CallToolResult, Tool } from "@modelcontextprotocol/sdk/types.js";

/**
 * Shape expected by MCP's `Tool.inputSchema` (a JSON Schema object type).
 * Aliased directly from the SDK's own inferred type (rather than a hand-rolled
 * structural copy) so hand-written schemas below are guaranteed to satisfy
 * whatever shape the installed SDK version actually expects for `tools/list`.
 */
export type ToolInputJsonSchema = Tool["inputSchema"];

/** A single text content block, as returned by MCP tool calls. */
export interface ToolTextContent {
  type: "text";
  text: string;
}

/**
 * The result shape every tool handler resolves to. Aliased from the SDK's
 * own `CallToolResult` type so it always matches what `Server`/`McpServer`
 * expect from a `tools/call` handler.
 */
export type ToolCallOutput = CallToolResult;

/** Public shape of a registered MCP tool. */
export interface ToolDefinition {
  name: string;
  description: string;
  /** Zod schema used for runtime validation inside the handler. */
  inputSchema: z.ZodTypeAny;
  /** Hand-written JSON Schema used for the MCP `tools/list` response. */
  jsonSchema: ToolInputJsonSchema;
  /** Validates `rawArgs`, calls the backend, and returns MCP content. */
  handler: (rawArgs: unknown) => Promise<ToolCallOutput>;
}

/**
 * Builds a ToolDefinition: validates raw arguments against `schema`, invokes
 * `execute` with the parsed, strictly-typed arguments, and wraps the
 * resolved value as pretty-printed JSON in a single text content block.
 */
export function defineTool<TArgs>(
  name: string,
  description: string,
  schema: z.ZodType<TArgs>,
  jsonSchema: ToolInputJsonSchema,
  execute: (args: TArgs) => Promise<unknown>
): ToolDefinition {
  return {
    name,
    description,
    inputSchema: schema,
    jsonSchema,
    async handler(rawArgs: unknown): Promise<ToolCallOutput> {
      const args = schema.parse(rawArgs ?? {});
      const result = await execute(args);
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(result, null, 2),
          },
        ],
      };
    },
  };
}

/**
 * Serializes GET/POST query parameters, skipping undefined values and
 * repeating the key for array values (FastAPI's `Query(default=[])` style).
 * Returns "" when nothing is set, otherwise a leading-"?" query string.
 */
export function buildQuery(
  params: Record<string, string | number | boolean | readonly string[] | undefined>
): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined) continue;
    if (Array.isArray(value)) {
      for (const item of value) search.append(key, String(item));
    } else {
      search.append(key, String(value));
    }
  }
  const qs = search.toString();
  return qs.length > 0 ? `?${qs}` : "";
}
