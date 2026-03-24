"use strict";
// ============================================================
// Character Management Tools (8 tools)
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
exports.characterToolDefs = void 0;
const zod_1 = require("zod");
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const renpy_generator_js_1 = require("../renpy-generator.js");
exports.characterToolDefs = [
    // 11. renpy_define_character
    {
        name: "renpy_define_character",
        description: "Define a Ren'Py Character object and append it to a definitions file.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Path to character definitions .rpy file"),
            id: zod_1.z.string().describe("Variable name (e.g. 'aria')"),
            name: zod_1.z.string().describe("Display name (e.g. 'Aria')"),
            color: zod_1.z.string().describe("Hex color for name (e.g. '#c8a0c8')"),
            voice_tag: zod_1.z.string().optional().describe("Voice tag for TTS"),
            what_font: zod_1.z.string().optional().describe("Font for dialogue text"),
            what_size: zod_1.z.number().optional().describe("Font size for dialogue text"),
            image: zod_1.z.string().optional().describe("Image tag for expressions"),
            callback: zod_1.z.string().optional().describe("Callback function name"),
        }),
        handler: async (args) => {
            const { file_path, ...def } = args;
            const code = (0, renpy_generator_js_1.generateCharacterDef)(def);
            let existing = "";
            if (fs.existsSync(file_path)) {
                existing = fs.readFileSync(file_path, "utf-8");
            }
            fs.mkdirSync(path.dirname(file_path), { recursive: true });
            fs.writeFileSync(file_path, existing + "\n" + code + "\n", "utf-8");
            return { content: [{ type: "text", text: `Defined character:\n${code}` }] };
        },
    },
    // 12. renpy_list_characters
    {
        name: "renpy_list_characters",
        description: "List all Character definitions found in .rpy files in a directory.",
        inputSchema: zod_1.z.object({
            search_dir: zod_1.z.string().describe("Directory to search"),
        }),
        handler: async (args) => {
            const entries = fs.readdirSync(args.search_dir, { recursive: true });
            const rpyFiles = entries
                .filter((e) => e.endsWith(".rpy"))
                .map((e) => path.join(args.search_dir, e));
            const chars = [];
            const re = /define\s+(\w+)\s*=\s*Character\(\s*"([^"]+)"(?:[^)]*?color="([^"]+)")?/gs;
            for (const file of rpyFiles) {
                const script = fs.readFileSync(file, "utf-8");
                let m;
                const localRe = new RegExp(re.source, re.flags);
                while ((m = localRe.exec(script)) !== null) {
                    chars.push({ file, id: m[1], name: m[2], color: m[3] ?? "#ffffff" });
                }
            }
            return {
                content: [
                    {
                        type: "text",
                        text: `Found ${chars.length} characters:\n\n${JSON.stringify(chars, null, 2)}`,
                    },
                ],
            };
        },
    },
    // 13. renpy_update_character
    {
        name: "renpy_update_character",
        description: "Update an existing Character definition in a .rpy file.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Path to the .rpy file"),
            id: zod_1.z.string().describe("Character variable name to update"),
            updates: zod_1.z
                .record(zod_1.z.string())
                .describe("Key-value pairs to update (color, name, voice_tag, etc.)"),
        }),
        handler: async (args) => {
            let script = fs.readFileSync(args.file_path, "utf-8");
            for (const [key, value] of Object.entries(args.updates)) {
                if (key === "name") {
                    // Update display name
                    const re = new RegExp(`(define\\s+${args.id}\\s*=\\s*Character\\(\\s*)"[^"]*"`);
                    script = script.replace(re, `$1"${value}"`);
                }
                else {
                    // Update named arg
                    const existingRe = new RegExp(`(define\\s+${args.id}[\\s\\S]*?${key}=)"[^"]*"`);
                    if (existingRe.test(script)) {
                        script = script.replace(existingRe, `$1"${value}"`);
                    }
                }
            }
            fs.writeFileSync(args.file_path, script, "utf-8");
            return {
                content: [
                    {
                        type: "text",
                        text: `Updated character '${args.id}' with: ${JSON.stringify(args.updates)}`,
                    },
                ],
            };
        },
    },
    // 14. renpy_add_character_expression
    {
        name: "renpy_add_character_expression",
        description: "Add an expression/pose image definition for a character (using 'image' statement).",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Path to character .rpy file"),
            character_id: zod_1.z.string().describe("Character image name prefix (e.g. 'aria')"),
            expression: zod_1.z
                .string()
                .describe("Expression name (e.g. 'happy', 'angry', 'blush')"),
            image_path: zod_1.z.string().describe("Relative path to the image file"),
        }),
        handler: async (args) => {
            const line = `image ${args.character_id} ${args.expression} = "${args.image_path}"`;
            let script = fs.existsSync(args.file_path)
                ? fs.readFileSync(args.file_path, "utf-8")
                : "";
            script = script.trimEnd() + "\n" + line + "\n";
            fs.writeFileSync(args.file_path, script, "utf-8");
            return {
                content: [{ type: "text", text: `Added expression:\n${line}` }],
            };
        },
    },
    // 15. renpy_generate_character_from_dna
    {
        name: "renpy_generate_character_from_dna",
        description: "Generate a full Ren'Py character definition from a SoulForge DNA profile.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Output .rpy file path"),
            dna: zod_1.z.object({
                name: zod_1.z.string(),
                archetype: zod_1.z.string(),
                affinity_type: zod_1.z.string(),
                corruption_vector: zod_1.z.string(),
                kink_profile: zod_1.z.array(zod_1.z.string()),
                voice_style: zod_1.z.string(),
                color_hex: zod_1.z.string(),
                sprite_style: zod_1.z.string(),
            }),
        }),
        handler: async (args) => {
            const code = (0, renpy_generator_js_1.generateCharacterFromDNA)(args.dna);
            let existing = fs.existsSync(args.file_path)
                ? fs.readFileSync(args.file_path, "utf-8")
                : "";
            fs.mkdirSync(path.dirname(args.file_path), { recursive: true });
            fs.writeFileSync(args.file_path, existing + "\n" + code + "\n", "utf-8");
            return { content: [{ type: "text", text: `Generated character from DNA:\n${code}` }] };
        },
    },
    // 16. renpy_add_character_sprite
    {
        name: "renpy_add_character_sprite",
        description: "Register a layered image sprite system for a character (Ren'Py layered_image).",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Output .rpy file path"),
            name: zod_1.z.string().describe("Image name (e.g. 'aria')"),
            base: zod_1.z.string().optional().describe("Base image path"),
            attributes: zod_1.z
                .array(zod_1.z.object({
                group: zod_1.z.string(),
                values: zod_1.z.array(zod_1.z.string()),
                default: zod_1.z.string().optional(),
            }))
                .describe("Attribute groups (outfit, expression, hair, etc.)"),
        }),
        handler: async (args) => {
            const config = {
                name: args.name,
                base: args.base,
                attributes: args.attributes,
            };
            const code = (0, renpy_generator_js_1.generateLayeredImage)(config);
            let existing = fs.existsSync(args.file_path)
                ? fs.readFileSync(args.file_path, "utf-8")
                : "";
            fs.writeFileSync(args.file_path, existing + "\n" + code + "\n", "utf-8");
            return {
                content: [{ type: "text", text: `Added layered image sprite:\n${code}` }],
            };
        },
    },
    // 17. renpy_define_character_voice
    {
        name: "renpy_define_character_voice",
        description: "Set character voice parameters in a voice configuration block.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Output .rpy file path"),
            character_id: zod_1.z.string().describe("Character variable ID"),
            voice_tag: zod_1.z.string().describe("Voice tag name"),
            voice_file_pattern: zod_1.z
                .string()
                .describe("Voice file pattern (e.g. 'audio/voice/aria/{id}.ogg')"),
            sustain: zod_1.z
                .boolean()
                .optional()
                .default(false)
                .describe("Sustain voice across menus"),
        }),
        handler: async (args) => {
            const lines = [
                `## Voice config: ${args.character_id}`,
                `define config.voice_tag_enabled = True`,
                `init python:`,
                `    def ${args.character_id}_voice_callback(event, **kwargs):`,
                `        if event == "begin":`,
                `            voice("${args.voice_file_pattern}")`,
                ``,
            ].join("\n");
            let existing = fs.existsSync(args.file_path)
                ? fs.readFileSync(args.file_path, "utf-8")
                : "";
            fs.writeFileSync(args.file_path, existing + "\n" + lines, "utf-8");
            return {
                content: [{ type: "text", text: `Voice config written:\n${lines}` }],
            };
        },
    },
    // 18. renpy_create_character_route
    {
        name: "renpy_create_character_route",
        description: "Create a complete character route skeleton with acts, key scenes, and jump structure.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Output .rpy file path"),
            character_id: zod_1.z.string().describe("Character ID (used for label prefixes)"),
            character_name: zod_1.z.string().describe("Display name"),
            acts: zod_1.z
                .number()
                .min(1)
                .max(10)
                .describe("Number of acts to scaffold"),
            scenes_per_act: zod_1.z
                .number()
                .min(1)
                .max(20)
                .describe("Number of scene labels per act"),
            include_affinity: zod_1.z
                .boolean()
                .optional()
                .default(true)
                .describe("Generate affinity tracking"),
        }),
        handler: async (args) => {
            const lines = [
                `## Route: ${args.character_name} (${args.character_id})`,
                `## Generated skeleton — fill in scene content`,
                ``,
            ];
            if (args.include_affinity) {
                lines.push(`default ${args.character_id}_affinity = 0`);
                lines.push(`default ${args.character_id}_route_active = False`);
                lines.push(``);
            }
            // Route entry
            lines.push(`label ${args.character_id}_route_start:`);
            lines.push(`    $ ${args.character_id}_route_active = True`);
            lines.push(`    jump ${args.character_id}_act1_scene1`);
            lines.push(``);
            for (let act = 1; act <= args.acts; act++) {
                lines.push(`## ═══ Act ${act} ═══`);
                for (let scene = 1; scene <= args.scenes_per_act; scene++) {
                    const label = `${args.character_id}_act${act}_scene${scene}`;
                    const next = scene < args.scenes_per_act
                        ? `${args.character_id}_act${act}_scene${scene + 1}`
                        : act < args.acts
                            ? `${args.character_id}_act${act + 1}_scene1`
                            : `${args.character_id}_route_end`;
                    lines.push(`label ${label}:`);
                    lines.push(`    ## Scene ${act}.${scene} — placeholder`);
                    lines.push(`    "## Dialogue placeholder"`);
                    lines.push(`    jump ${next}`);
                    lines.push(``);
                }
            }
            lines.push(`label ${args.character_id}_route_end:`);
            lines.push(`    ## Route complete`);
            lines.push(`    return`);
            const content = lines.join("\n");
            fs.mkdirSync(path.dirname(args.file_path), { recursive: true });
            fs.writeFileSync(args.file_path, content, "utf-8");
            return {
                content: [
                    {
                        type: "text",
                        text: `Route skeleton created at ${args.file_path}\n${args.acts} acts × ${args.scenes_per_act} scenes = ${args.acts * args.scenes_per_act} labels`,
                    },
                ],
            };
        },
    },
];
//# sourceMappingURL=character-tools.js.map