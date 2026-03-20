"use strict";
// ============================================================
// Variable & Logic Tools (8 tools)
// ============================================================
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.logicToolDefs = void 0;
const zod_1 = require("zod");
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const renpy_generator_js_1 = require("../renpy-generator.js");
exports.logicToolDefs = [
    // 27. renpy_define_variable
    {
        name: "renpy_define_variable",
        description: "Define a game variable with a default value, with optional type annotation comment.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Path to variables .rpy file"),
            name: zod_1.z.string().describe("Variable name"),
            value: zod_1.z.string().describe("Default value (Python literal)"),
            is_define: zod_1.z
                .boolean()
                .optional()
                .default(false)
                .describe("Use 'define' instead of 'default' (for constants)"),
            description: zod_1.z
                .string()
                .optional()
                .describe("Optional comment describing the variable"),
        }),
        handler: async (args) => {
            const comment = args.description ? `## ${args.description}\n` : "";
            const line = args.is_define
                ? (0, renpy_generator_js_1.generateDefine)(args.name, args.value)
                : (0, renpy_generator_js_1.generateDefault)(args.name, args.value);
            let existing = fs.existsSync(args.file_path)
                ? fs.readFileSync(args.file_path, "utf-8")
                : "";
            fs.mkdirSync(path.dirname(args.file_path), { recursive: true });
            fs.writeFileSync(args.file_path, existing + "\n" + comment + line + "\n", "utf-8");
            return {
                content: [{ type: "text", text: `Defined variable:\n${comment}${line}` }],
            };
        },
    },
    // 28. renpy_add_condition
    {
        name: "renpy_add_condition",
        description: "Add an if/elif/else conditional block to a .rpy file.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Path to .rpy file"),
            conditions: zod_1.z
                .array(zod_1.z.object({
                condition: zod_1.z.string().describe("Python condition expression"),
                body: zod_1.z.array(zod_1.z.string()).describe("Lines to execute"),
            }))
                .describe("if/elif branches"),
            else_body: zod_1.z
                .array(zod_1.z.string())
                .optional()
                .describe("else branch lines"),
            indent_level: zod_1.z
                .number()
                .optional()
                .default(1)
                .describe("Base indentation level (1 = 4 spaces)"),
        }),
        handler: async (args) => {
            const pad = "    ".repeat(args.indent_level);
            const block = (0, renpy_generator_js_1.generateConditionBlock)(args.conditions, args.else_body);
            const indented = block
                .split("\n")
                .map((l) => (l.trim() ? pad + l : l))
                .join("\n");
            let script = fs.readFileSync(args.file_path, "utf-8");
            script = script.trimEnd() + "\n" + indented + "\n";
            fs.writeFileSync(args.file_path, script, "utf-8");
            return { content: [{ type: "text", text: `Added condition block:\n${indented}` }] };
        },
    },
    // 29. renpy_add_python_block
    {
        name: "renpy_add_python_block",
        description: "Add an inline Python block to a .rpy file.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Path to .rpy file"),
            code: zod_1.z.string().describe("Python code to insert"),
            is_init: zod_1.z
                .boolean()
                .optional()
                .default(false)
                .describe("Use 'init python:' block instead of 'python:'"),
            init_priority: zod_1.z
                .number()
                .optional()
                .describe("Init block priority (if is_init)"),
        }),
        handler: async (args) => {
            const header = args.is_init
                ? args.init_priority !== undefined
                    ? `init ${args.init_priority} python:`
                    : `init python:`
                : `python:`;
            const indented = args.code
                .split("\n")
                .map((l) => `    ${l}`)
                .join("\n");
            const block = `${header}\n${indented}\n`;
            let script = fs.readFileSync(args.file_path, "utf-8");
            script = script.trimEnd() + "\n\n" + block;
            fs.writeFileSync(args.file_path, script, "utf-8");
            return { content: [{ type: "text", text: `Added python block:\n${block}` }] };
        },
    },
    // 30. renpy_define_screen
    {
        name: "renpy_define_screen",
        description: "Create a Ren'Py screen definition and append to a .rpy file.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Path to screens .rpy file"),
            name: zod_1.z.string().describe("Screen name"),
            params: zod_1.z
                .array(zod_1.z.string())
                .optional()
                .describe("Screen parameters"),
            body: zod_1.z.string().describe("Screen body (indented Ren'Py screen language)"),
        }),
        handler: async (args) => {
            const code = (0, renpy_generator_js_1.generateScreen)({ name: args.name, params: args.params, body: args.body });
            let existing = fs.existsSync(args.file_path)
                ? fs.readFileSync(args.file_path, "utf-8")
                : "";
            fs.mkdirSync(path.dirname(args.file_path), { recursive: true });
            fs.writeFileSync(args.file_path, existing + "\n\n" + code + "\n", "utf-8");
            return { content: [{ type: "text", text: `Screen defined:\n${code}` }] };
        },
    },
    // 31. renpy_add_transform
    {
        name: "renpy_add_transform",
        description: "Add an ATL transform definition to a .rpy file.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Path to transforms .rpy file"),
            name: zod_1.z.string().describe("Transform name"),
            body: zod_1.z
                .string()
                .describe("ATL body (e.g. 'xalign 0.5\\nyalign 1.0\\npause 0.5\\nrepeat')"),
        }),
        handler: async (args) => {
            const code = (0, renpy_generator_js_1.generateATLTransform)({ name: args.name, body: args.body });
            let existing = fs.existsSync(args.file_path)
                ? fs.readFileSync(args.file_path, "utf-8")
                : "";
            fs.writeFileSync(args.file_path, existing + "\n" + code + "\n", "utf-8");
            return { content: [{ type: "text", text: `Transform added:\n${code}` }] };
        },
    },
    // 32. renpy_track_affinity
    {
        name: "renpy_track_affinity",
        description: "Generate affinity tracking defaults and helper label for a character.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Output .rpy file path"),
            character_id: zod_1.z.string().describe("Character ID"),
            variable_name: zod_1.z.string().describe("Affinity variable name (e.g. 'aria_affinity')"),
            thresholds: zod_1.z.object({
                low: zod_1.z.number().default(10),
                medium: zod_1.z.number().default(30),
                high: zod_1.z.number().default(60),
                max: zod_1.z.number().default(100),
            }),
            route_unlock_threshold: zod_1.z.number().describe("Threshold to unlock route"),
        }),
        handler: async (args) => {
            const cfg = {
                character_id: args.character_id,
                variable_name: args.variable_name,
                thresholds: args.thresholds,
                route_unlock_threshold: args.route_unlock_threshold,
            };
            const code = (0, renpy_generator_js_1.generateAffinityDefaults)(cfg);
            let existing = fs.existsSync(args.file_path)
                ? fs.readFileSync(args.file_path, "utf-8")
                : "";
            fs.mkdirSync(path.dirname(args.file_path), { recursive: true });
            fs.writeFileSync(args.file_path, existing + "\n" + code + "\n", "utf-8");
            return { content: [{ type: "text", text: `Affinity tracking added:\n${code}` }] };
        },
    },
    // 33. renpy_add_flag
    {
        name: "renpy_add_flag",
        description: "Add a story flag variable (boolean default False) with a description comment.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Path to flags .rpy file"),
            flag_name: zod_1.z.string().describe("Flag variable name (e.g. 'aria_told_truth')"),
            description: zod_1.z.string().describe("Human-readable flag description"),
            default_value: zod_1.z
                .boolean()
                .optional()
                .default(false)
                .describe("Initial value"),
        }),
        handler: async (args) => {
            const val = args.default_value ? "True" : "False";
            const lines = [
                `## FLAG: ${args.flag_name} — ${args.description}`,
                `default ${args.flag_name} = ${val}`,
            ].join("\n");
            let existing = fs.existsSync(args.file_path)
                ? fs.readFileSync(args.file_path, "utf-8")
                : "";
            fs.mkdirSync(path.dirname(args.file_path), { recursive: true });
            fs.writeFileSync(args.file_path, existing + "\n" + lines + "\n", "utf-8");
            return { content: [{ type: "text", text: `Flag added:\n${lines}` }] };
        },
    },
    // 34. renpy_create_ending
    {
        name: "renpy_create_ending",
        description: "Create one of the 8 EoBQ ending types with conditions, music, and CG stubs.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Output .rpy file path"),
            type: zod_1.z
                .enum([
                "true_love",
                "corruption_complete",
                "harem_empress",
                "burned_out",
                "queen_ascendant",
                "mutual_destruction",
                "secret_escape",
                "bad_end",
            ])
                .describe("Ending type"),
            label: zod_1.z.string().describe("Ending label name"),
            conditions: zod_1.z.array(zod_1.z.string()).describe("Conditions required to reach this ending"),
            title: zod_1.z.string().describe("Ending title shown to player"),
            music: zod_1.z.string().optional().describe("Ending music file"),
            cg: zod_1.z.string().optional().describe("Ending CG image name"),
            description: zod_1.z.string().describe("Narrative description of the ending"),
        }),
        handler: async (args) => {
            const cfg = {
                type: args.type,
                label: args.label,
                conditions: args.conditions,
                title: args.title,
                music: args.music,
                cg: args.cg,
                description: args.description,
            };
            const code = (0, renpy_generator_js_1.generateEnding)(cfg);
            let existing = fs.existsSync(args.file_path)
                ? fs.readFileSync(args.file_path, "utf-8")
                : "";
            fs.mkdirSync(path.dirname(args.file_path), { recursive: true });
            fs.writeFileSync(args.file_path, existing + "\n" + code + "\n", "utf-8");
            return { content: [{ type: "text", text: `Ending created:\n${code}` }] };
        },
    },
];
//# sourceMappingURL=logic-tools.js.map