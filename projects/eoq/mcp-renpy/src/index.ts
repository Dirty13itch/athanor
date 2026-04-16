#!/usr/bin/env node
// ============================================================
// mcp-renpy — Ren'Py MCP Server for EoBQ SoulForge Engine
// ============================================================

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from "@modelcontextprotocol/sdk/types.js";
import { z, ZodSchema, ZodObject } from "zod";

import { scriptToolDefs } from "./tools/script-tools.js";
import { characterToolDefs } from "./tools/character-tools.js";
import { sceneToolDefs } from "./tools/scene-tools.js";
import { logicToolDefs } from "./tools/logic-tools.js";
import { projectToolDefs } from "./tools/project-tools.js";
import { eoqToolDefs } from "./tools/eoq-tools.js";

// ── Tool registry ──────────────────────────────────────────────

interface ToolDef {
  name: string;
  description: string;
  inputSchema: ZodObject<any>;
  handler: (args: any) => Promise<any>;
}

const ALL_TOOLS: ToolDef[] = [
  ...scriptToolDefs,
  ...characterToolDefs,
  ...sceneToolDefs,
  ...logicToolDefs,
  ...projectToolDefs,
  ...eoqToolDefs,
] as ToolDef[];

const toolMap = new Map<string, ToolDef>(
  ALL_TOOLS.map((t) => [t.name, t])
);

// ── Convert Zod schema to JSON Schema (simple) ─────────────────

function zodToJsonSchema(schema: ZodObject<any>): object {
  const shape = schema.shape;
  const properties: Record<string, any> = {};
  const required: string[] = [];

  for (const [key, value] of Object.entries(shape)) {
    const zodValue = value as ZodSchema;
    const def = (zodValue as any)._def;
    const prop = zodFieldToJson(zodValue);
    properties[key] = prop;

    // If not optional, mark as required
    if (def.typeName !== "ZodOptional" && def.typeName !== "ZodDefault") {
      required.push(key);
    }
  }

  return {
    type: "object",
    properties,
    required: required.length > 0 ? required : undefined,
  };
}

function zodFieldToJson(field: ZodSchema): any {
  const def = (field as any)._def;
  const typeName: string = def.typeName;

  switch (typeName) {
    case "ZodString":
      return { type: "string", description: def.description };
    case "ZodNumber":
      return {
        type: "number",
        description: def.description,
        minimum: def.checks?.find((c: any) => c.kind === "min")?.value,
        maximum: def.checks?.find((c: any) => c.kind === "max")?.value,
      };
    case "ZodBoolean":
      return { type: "boolean", description: def.description };
    case "ZodArray":
      return {
        type: "array",
        items: zodFieldToJson(def.type),
        description: def.description,
      };
    case "ZodObject":
      return zodToJsonSchema(field as ZodObject<any>);
    case "ZodEnum":
      return {
        type: "string",
        enum: def.values,
        description: def.description,
      };
    case "ZodOptional":
      return zodFieldToJson(def.innerType);
    case "ZodDefault":
      return { ...zodFieldToJson(def.innerType), default: def.defaultValue() };
    case "ZodRecord":
      return {
        type: "object",
        additionalProperties: zodFieldToJson(def.valueType),
        description: def.description,
      };
    case "ZodUnion":
      return { oneOf: def.options.map(zodFieldToJson) };
    case "ZodLiteral":
      return { type: typeof def.value, const: def.value };
    default:
      return { type: "string", description: `(${typeName})` };
  }
}

// ── MCP Server ─────────────────────────────────────────────────

const server = new Server(
  {
    name: "mcp-renpy",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// List tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  const tools: Tool[] = ALL_TOOLS.map((t) => ({
    name: t.name,
    description: t.description,
    inputSchema: zodToJsonSchema(t.inputSchema) as Tool["inputSchema"],
  }));

  return { tools };
});

// Call tool
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  const toolDef = toolMap.get(name);
  if (!toolDef) {
    return {
      content: [
        {
          type: "text",
          text: `Unknown tool: ${name}. Available tools: ${ALL_TOOLS.map((t) => t.name).join(", ")}`,
        },
      ],
      isError: true,
    };
  }

  try {
    // Validate and parse args through zod
    const parsed = toolDef.inputSchema.parse(args ?? {});
    const result = await toolDef.handler(parsed);
    return result;
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    const stack = err instanceof Error ? err.stack ?? "" : "";
    return {
      content: [
        {
          type: "text",
          text: `Error in ${name}:\n${message}\n${stack}`,
        },
      ],
      isError: true,
    };
  }
});

// ── Start ──────────────────────────────────────────────────────

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);

  // Log to stderr so it doesn't interfere with MCP stdio protocol
  process.stderr.write(
    `mcp-renpy v1.0.0 started — ${ALL_TOOLS.length} tools loaded\n`
  );
  process.stderr.write(
    `Categories: script(10) character(8) scene(8) logic(8) project(8) eoq(8)\n`
  );
}

main().catch((err) => {
  process.stderr.write(`Fatal: ${err}\n`);
  process.exit(1);
});
