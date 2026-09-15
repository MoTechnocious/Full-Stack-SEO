#!/usr/bin/env node
/**
 * Entrypoint for the MySEOapp MCP server.
 *
 * Connects the server to stdio, per the MCP stdio transport convention:
 * JSON-RPC messages go over stdin/stdout, so all diagnostic logging here
 * must go to stderr (via console.error) to avoid corrupting the protocol
 * stream.
 */

import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { createServer, SERVER_NAME, SERVER_VERSION } from "./server.js";
import { config } from "./config.js";

/** Describes which auth header (if any) is configured, for the startup log line. */
function describeAuthMode(): string {
  if (config.apiKey) {
    return "X-API-Key";
  }
  if (config.token) {
    return "Authorization: Bearer";
  }
  return "none (requests will fail with 401 until MYSEOAPP_API_KEY or MYSEOAPP_TOKEN is set)";
}

async function main(): Promise<void> {
  const server = createServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);

  console.error(
    `[${SERVER_NAME}] v${SERVER_VERSION} ready on stdio ` +
      `(backend: ${config.apiBaseUrl}, auth: ${describeAuthMode()})`
  );
}

main().catch((error: unknown) => {
  console.error("[myseoapp-mcp] fatal error during startup:", error);
  process.exitCode = 1;
});
