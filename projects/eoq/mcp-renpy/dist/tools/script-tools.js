"use strict";
// ============================================================
// Script Management Tools (10 tools)
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
exports.scriptToolDefs = void 0;
const zod_1 = require("zod");
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const renpy_generator_js_1 = require("../renpy-generator.js");
exports.scriptToolDefs = [
    // 1. renpy_create_script
    {
        name: "renpy_create_script",
        description: "Create a new .rpy script file with boilerplate. Returns the path of the created file.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Absolute path for the new .rpy file"),
            label: zod_1.z.string().describe("Initial label name to create"),
            description: zod_1.z.string().describe("Human-readable file description"),
            include_defaults: zod_1.z
                .boolean()
                .optional()
                .default(true)
                .describe("Include default boilerplate (init block, etc.)"),
        }),
        handler: async (args) => {
            const header = (0, renpy_generator_js_1.fileHeader)(args.description);
            const body = [
                `"## Scene placeholder"`,
                `return`,
            ];
            const labelBlock = (0, renpy_generator_js_1.generateLabel)(args.label, body);
            let content = header + "\n";
            if (args.include_defaults) {
                content += `init python:\n    pass\n\n`;
            }
            content += labelBlock;
            fs.mkdirSync(path.dirname(args.file_path), { recursive: true });
            fs.writeFileSync(args.file_path, content, "utf-8");
            return {
                content: [{ type: "text", text: `Created: ${args.file_path}\n\n${content}` }],
            };
        },
    },
    // 2. renpy_parse_script
    {
        name: "renpy_parse_script",
        description: "Parse an existing .rpy file and return a structured summary of labels, characters, and jumps.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Path to the .rpy file to parse"),
        }),
        handler: async (args) => {
            const script = fs.readFileSync(args.file_path, "utf-8");
            const nodes = (0, renpy_generator_js_1.parseFlowchart)(script);
            const labels = nodes.map((n) => n.label);
            const allJumps = nodes.flatMap((n) => n.jumps);
            const allCalls = nodes.flatMap((n) => n.calls);
            // Extract character definitions
            const charRegex = /define\s+(\w+)\s*=\s*Character\(/g;
            const chars = [];
            let m;
            while ((m = charRegex.exec(script)) !== null)
                chars.push(m[1]);
            const summary = {
                file: args.file_path,
                line_count: script.split("\n").length,
                labels,
                characters: chars,
                jumps: [...new Set(allJumps)],
                calls: [...new Set(allCalls)],
                nodes,
            };
            return {
                content: [{ type: "text", text: JSON.stringify(summary, null, 2) }],
            };
        },
    },
    // 3. renpy_validate_script
    {
        name: "renpy_validate_script",
        description: "Validate a .rpy file for syntax errors (unclosed quotes, duplicate labels, unresolved jumps).",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z
                .string()
                .optional()
                .describe("Path to .rpy file (mutually exclusive with content)"),
            content: zod_1.z
                .string()
                .optional()
                .describe("Raw script content to validate"),
        }),
        handler: async (args) => {
            let script = args.content ?? "";
            if (args.file_path && !args.content) {
                script = fs.readFileSync(args.file_path, "utf-8");
            }
            const result = (0, renpy_generator_js_1.validateScript)(script);
            const lines = [
                `Valid: ${result.valid}`,
                `Errors (${result.errors.length}):`,
                ...result.errors.map((e) => `  ERROR: ${e}`),
                `Warnings (${result.warnings.length}):`,
                ...result.warnings.map((w) => `  WARN: ${w}`),
            ];
            return { content: [{ type: "text", text: lines.join("\n") }] };
        },
    },
    // 4. renpy_list_labels
    {
        name: "renpy_list_labels",
        description: "List all label names defined in a .rpy file or directory.",
        inputSchema: zod_1.z.object({
            path: zod_1.z.string().describe("Path to .rpy file or directory"),
        }),
        handler: async (args) => {
            const stat = fs.statSync(args.path);
            const files = [];
            if (stat.isDirectory()) {
                const entries = fs.readdirSync(args.path, { recursive: true });
                files.push(...entries
                    .filter((e) => e.endsWith(".rpy"))
                    .map((e) => path.join(args.path, e)));
            }
            else {
                files.push(args.path);
            }
            const result = {};
            for (const f of files) {
                const script = fs.readFileSync(f, "utf-8");
                const labels = [];
                const re = /^label\s+(\w+)\s*:/gm;
                let m;
                while ((m = re.exec(script)) !== null)
                    labels.push(m[1]);
                result[f] = labels;
            }
            return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
        },
    },
    // 5. renpy_find_references
    {
        name: "renpy_find_references",
        description: "Find all references (jumps, calls, show commands) to a given label or variable name across .rpy files.",
        inputSchema: zod_1.z.object({
            search_dir: zod_1.z.string().describe("Directory to search"),
            symbol: zod_1.z.string().describe("Label or variable name to find"),
        }),
        handler: async (args) => {
            const entries = fs.readdirSync(args.search_dir, { recursive: true });
            const rpyFiles = entries
                .filter((e) => e.endsWith(".rpy"))
                .map((e) => path.join(args.search_dir, e));
            const refs = [];
            const pattern = new RegExp(`\\b${args.symbol}\\b`, "g");
            for (const file of rpyFiles) {
                const lines = fs.readFileSync(file, "utf-8").split("\n");
                lines.forEach((line, i) => {
                    if (pattern.test(line)) {
                        refs.push({ file, line: i + 1, text: line.trim() });
                    }
                    pattern.lastIndex = 0;
                });
            }
            return {
                content: [
                    {
                        type: "text",
                        text: `Found ${refs.length} references to "${args.symbol}":\n\n${JSON.stringify(refs, null, 2)}`,
                    },
                ],
            };
        },
    },
    // 6. renpy_add_dialogue
    {
        name: "renpy_add_dialogue",
        description: "Append a dialogue line to an existing .rpy file (at end or after a label).",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Path to the .rpy file"),
            speaker: zod_1.z.string().describe("Character variable name (e.g. 'aria')"),
            text: zod_1.z.string().describe("Dialogue text"),
            tag: zod_1.z.string().optional().describe("Expression tag (e.g. 'smile')"),
            after_label: zod_1.z
                .string()
                .optional()
                .describe("Insert after this label instead of appending"),
        }),
        handler: async (args) => {
            let script = fs.readFileSync(args.file_path, "utf-8");
            const line = `    ${(0, renpy_generator_js_1.generateDialogue)(args.speaker, args.text, args.tag)}`;
            if (args.after_label) {
                const re = new RegExp(`(label\\s+${args.after_label}\\s*:[^\\n]*)`, "");
                script = script.replace(re, `$1\n${line}`);
            }
            else {
                script = script.trimEnd() + "\n" + line + "\n";
            }
            fs.writeFileSync(args.file_path, script, "utf-8");
            return { content: [{ type: "text", text: `Added dialogue to ${args.file_path}:\n${line}` }] };
        },
    },
    // 7. renpy_add_choice_menu
    {
        name: "renpy_add_choice_menu",
        description: "Add a choice menu block to a .rpy file.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Path to the .rpy file to append to"),
            label: zod_1.z.string().describe("Label to insert the menu under"),
            prompt: zod_1.z.string().describe("Menu prompt text (shown above choices)"),
            options: zod_1.z
                .array(zod_1.z.object({
                text: zod_1.z.string(),
                jump: zod_1.z.string().optional(),
                condition: zod_1.z.string().optional(),
                affinity_delta: zod_1.z.record(zod_1.z.number()).optional(),
            }))
                .describe("Array of choice options"),
        }),
        handler: async (args) => {
            let script = fs.readFileSync(args.file_path, "utf-8");
            const menuBlock = (0, renpy_generator_js_1.generateChoiceMenu)(args.prompt, args.options);
            const indented = menuBlock
                .split("\n")
                .map((l) => `    ${l}`)
                .join("\n");
            const re = new RegExp(`(label\\s+${args.label}\\s*:)`, "");
            if (re.test(script)) {
                script = script.replace(re, `$1\n${indented}`);
            }
            else {
                script += `\n\nlabel ${args.label}:\n${indented}\n    return\n`;
            }
            fs.writeFileSync(args.file_path, script, "utf-8");
            return {
                content: [{ type: "text", text: `Added choice menu to ${args.file_path}\n\n${indented}` }],
            };
        },
    },
    // 8. renpy_add_narration
    {
        name: "renpy_add_narration",
        description: "Append a narration block (narrator text) to a .rpy file.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Path to the .rpy file"),
            text: zod_1.z.string().describe("Narration text"),
            after_label: zod_1.z.string().optional().describe("Insert after this label"),
        }),
        handler: async (args) => {
            let script = fs.readFileSync(args.file_path, "utf-8");
            const line = `    ${(0, renpy_generator_js_1.generateNarration)(args.text)}`;
            if (args.after_label) {
                const re = new RegExp(`(label\\s+${args.after_label}\\s*:)`);
                script = script.replace(re, `$1\n${line}`);
            }
            else {
                script = script.trimEnd() + "\n" + line + "\n";
            }
            fs.writeFileSync(args.file_path, script, "utf-8");
            return { content: [{ type: "text", text: `Added narration:\n${line}` }] };
        },
    },
    // 9. renpy_merge_scripts
    {
        name: "renpy_merge_scripts",
        description: "Merge two .rpy files into one, with conflict detection.",
        inputSchema: zod_1.z.object({
            file_a: zod_1.z.string().describe("First .rpy file path"),
            file_b: zod_1.z.string().describe("Second .rpy file path"),
            output: zod_1.z.string().describe("Output file path"),
        }),
        handler: async (args) => {
            const a = fs.readFileSync(args.file_a, "utf-8");
            const b = fs.readFileSync(args.file_b, "utf-8");
            const merged = (0, renpy_generator_js_1.mergeScripts)(a, b);
            const validation = (0, renpy_generator_js_1.validateScript)(merged);
            fs.writeFileSync(args.output, merged, "utf-8");
            return {
                content: [
                    {
                        type: "text",
                        text: [
                            `Merged to: ${args.output}`,
                            `Lines: ${merged.split("\n").length}`,
                            `Valid: ${validation.valid}`,
                            ...validation.errors.map((e) => `ERROR: ${e}`),
                            ...validation.warnings.map((w) => `WARN: ${w}`),
                        ].join("\n"),
                    },
                ],
            };
        },
    },
    // 10. renpy_extract_strings
    {
        name: "renpy_extract_strings",
        description: "Extract all translatable strings from a .rpy file or directory for localization.",
        inputSchema: zod_1.z.object({
            path: zod_1.z.string().describe("Path to .rpy file or directory"),
            output_json: zod_1.z
                .string()
                .optional()
                .describe("If provided, write JSON output to this path"),
        }),
        handler: async (args) => {
            const stat = fs.statSync(args.path);
            const files = [];
            if (stat.isDirectory()) {
                const entries = fs.readdirSync(args.path, { recursive: true });
                files.push(...entries
                    .filter((e) => e.endsWith(".rpy"))
                    .map((e) => path.join(args.path, e)));
            }
            else {
                files.push(args.path);
            }
            const allStrings = {};
            for (const f of files) {
                const script = fs.readFileSync(f, "utf-8");
                allStrings[f] = (0, renpy_generator_js_1.extractTranslatableStrings)(script);
            }
            const json = JSON.stringify(allStrings, null, 2);
            if (args.output_json) {
                fs.writeFileSync(args.output_json, json, "utf-8");
            }
            const total = Object.values(allStrings).reduce((s, a) => s + a.length, 0);
            return {
                content: [
                    {
                        type: "text",
                        text: `Extracted ${total} strings from ${files.length} files.\n\n${json}`,
                    },
                ],
            };
        },
    },
];
//# sourceMappingURL=script-tools.js.map