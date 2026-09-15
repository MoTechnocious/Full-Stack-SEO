/**
 * Wires the MySEOapp tool definitions into an MCP `Server` instance.
 *
 * This intentionally uses the SDK's low-level `Server` (rather than the
 * higher-level `McpServer` convenience wrapper) so that:
 *  - the `tools/list` response is built directly from our hand-written JSON
 *    Schemas (see src/tools/index.ts), with no implicit Zod -> JSON Schema
 *    conversion step, and
 *  - `tools/call` dispatch and error formatting are fully explicit.
 *
 * The SDK marks `Server` as deprecated in favor of `McpServer` for typical
 * use cases, but keeps it available for exactly this kind of advanced,
 * manual control over tool listing/dispatch — which is what this server
 * needs.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  type CallToolRequest,
  type CallToolResult,
  type ListToolsResult,
  type Tool,
} from "@modelcontextprotocol/sdk/types.js";
import { tools, type ToolDefinition } from "./tools/index.js";

export const SERVER_NAME = "myseoapp-mcp";
/** Keep in sync with the "version" field in package.json. */
export const SERVER_VERSION = "0.1.0";

function toMcpTool(tool: ToolDefinition): Tool {
  return {
    name: tool.name,
    description: tool.description,
    inputSchema: tool.jsonSchema,
  };
}

function formatError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return typeof error === "string" ? error : JSON.stringify(error);
}

function findTool(name: string): ToolDefinition | undefined {
  return tools.find((tool) => tool.name === name);
}

async function handleCallTool(request: CallToolRequest): Promise<CallToolResult> {
  const { name, arguments: rawArgs } = request.params;
  const tool = findTool(name);

  if (!tool) {
    return {
      content: [{ type: "text", text: `Unknown tool: "${name}"` }],
      isError: true,
    };
  }

  try {
    return await tool.handler(rawArgs);
  } catch (error) {
    return {
      content: [{ type: "text", text: `Error calling "${name}": ${formatError(error)}` }],
      isError: true,
    };
  }
}

/** Creates a new MCP `Server`, with the MySEOapp tools registered. */
export function createServer(): Server {
  const server = new Server(
    { name: SERVER_NAME, version: SERVER_VERSION },
    { capabilities: { tools: {} } }
  );

  server.setRequestHandler(ListToolsRequestSchema, async (): Promise<ListToolsResult> => {
    return { tools: tools.map(toMcpTool) };
  });

  server.setRequestHandler(CallToolRequestSchema, async (request): Promise<CallToolResult> => {
    return handleCallTool(request);
  });

  return server;
}
