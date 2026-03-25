#!/usr/bin/env node
"use strict";
// ============================================================
// mcp-renpy — Ren'Py MCP Server for EoBQ SoulForge Engine
// ============================================================
Object.defineProperty(exports, "__esModule", { value: true });
const index_js_1 = require("@modelcontextprotocol/sdk/server/index.js");
const stdio_js_1 = require("@modelcontextprotocol/sdk/server/stdio.js");
const types_js_1 = require("@modelcontextprotocol/sdk/types.js");
const script_tools_js_1 = require("./tools/script-tools.js");
const character_tools_js_1 = require("./tools/character-tools.js");
const scene_tools_js_1 = require("./tools/scene-tools.js");
const logic_tools_js_1 = require("./tools/logic-tools.js");
const project_tools_js_1 = require("./tools/project-tools.js");
const eoq_tools_js_1 = require("./tools/eoq-tools.js");
const ALL_TOOLS = [
    ...script_tools_js_1.scriptToolDefs,
    ...character_tools_js_1.characterToolDefs,
    ...scene_tools_js_1.sceneToolDefs,
    ...logic_tools_js_1.logicToolDefs,
    ...project_tools_js_1.projectToolDefs,
    ...eoq_tools_js_1.eoqToolDefs,
];
const toolMap = new Map(ALL_TOOLS.map((t) => [t.name, t]));
// ── Convert Zod schema to JSON Schema (simple) ─────────────────
function zodToJsonSchema(schema) {
    const shape = schema.shape;
    const properties = {};
    const required = [];
    for (const [key, value] of Object.entries(shape)) {
        const zodValue = value;
        const def = zodValue._def;
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
function zodFieldToJson(field) {
    const def = field._def;
    const typeName = def.typeName;
    switch (typeName) {
        case "ZodString":
            return { type: "string", description: def.description };
        case "ZodNumber":
            return {
                type: "number",
                description: def.description,
                minimum: def.checks?.find((c) => c.kind === "min")?.value,
                maximum: def.checks?.find((c) => c.kind === "max")?.value,
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
            return zodToJsonSchema(field);
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
const server = new index_js_1.Server({
    name: "mcp-renpy",
    version: "1.0.0",
}, {
    capabilities: {
        tools: {},
    },
});
// List tools
server.setRequestHandler(types_js_1.ListToolsRequestSchema, async () => {
    const tools = ALL_TOOLS.map((t) => ({
        name: t.name,
        description: t.description,
        inputSchema: zodToJsonSchema(t.inputSchema),
    }));
    return { tools };
});
// Call tool
server.setRequestHandler(types_js_1.CallToolRequestSchema, async (request) => {
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
    }
    catch (err) {
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
    const transport = new stdio_js_1.StdioServerTransport();
    await server.connect(transport);
    // Log to stderr so it doesn't interfere with MCP stdio protocol
    process.stderr.write(`mcp-renpy v1.0.0 started — ${ALL_TOOLS.length} tools loaded\n`);
    process.stderr.write(`Categories: script(10) character(8) scene(8) logic(8) project(8) eoq(8)\n`);
}
main().catch((err) => {
    process.stderr.write(`Fatal: ${err}\n`);
    process.exit(1);
});
//# sourceMappingURL=index.js.map