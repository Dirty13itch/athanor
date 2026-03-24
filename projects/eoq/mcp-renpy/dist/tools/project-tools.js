"use strict";
// ============================================================
// Project Management Tools (8 tools)
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
exports.projectToolDefs = void 0;
const zod_1 = require("zod");
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const child_process = __importStar(require("child_process"));
const renpy_generator_js_1 = require("../renpy-generator.js");
exports.projectToolDefs = [
    // 35. renpy_init_project
    {
        name: "renpy_init_project",
        description: "Initialize a new Ren'Py project directory structure with standard files.",
        inputSchema: zod_1.z.object({
            base_dir: zod_1.z.string().describe("Root directory for the project"),
            name: zod_1.z.string().describe("Game name"),
            build_name: zod_1.z
                .string()
                .describe("Build name (no spaces, used for file names)"),
            version: zod_1.z.string().default("1.0.0").describe("Game version"),
            developer: zod_1.z.string().describe("Developer name"),
            copyright: zod_1.z.string().describe("Copyright string"),
        }),
        handler: async (args) => {
            const dirs = [
                "game/images/characters",
                "game/images/backgrounds",
                "game/images/cg",
                "game/audio/music",
                "game/audio/sfx",
                "game/audio/voice",
                "game/scripts",
                "game/gui",
                "game/saves",
                "game/tl/english",
            ];
            for (const d of dirs) {
                fs.mkdirSync(path.join(args.base_dir, d), { recursive: true });
            }
            // options.rpy
            const options = (0, renpy_generator_js_1.generateProjectOptions)({
                name: args.name,
                build_name: args.build_name,
                version: args.version,
                developer: args.developer,
                copyright: args.copyright,
            });
            fs.writeFileSync(path.join(args.base_dir, "game/options.rpy"), `## Game options\n\n${options}\n`, "utf-8");
            // script.rpy
            fs.writeFileSync(path.join(args.base_dir, "game/script.rpy"), [
                `## Main script entry point`,
                ``,
                `label start:`,
                `    "## Game start — replace with opening scene"`,
                `    jump main_menu`,
                ``,
                `label main_menu:`,
                `    return`,
            ].join("\n"), "utf-8");
            // characters.rpy
            fs.writeFileSync(path.join(args.base_dir, "game/scripts/characters.rpy"), `## Character definitions\n\n`, "utf-8");
            // variables.rpy
            fs.writeFileSync(path.join(args.base_dir, "game/scripts/variables.rpy"), `## Game variables and defaults\n\n`, "utf-8");
            // screens.rpy stub
            fs.writeFileSync(path.join(args.base_dir, "game/scripts/screens.rpy"), `## Custom screens\n\n`, "utf-8");
            const created = dirs.map((d) => path.join(args.base_dir, d));
            return {
                content: [
                    {
                        type: "text",
                        text: [
                            `Project initialized at: ${args.base_dir}`,
                            `Name: ${args.name} v${args.version}`,
                            `Directories created: ${dirs.length}`,
                            ``,
                            dirs.map((d) => `  ${d}`).join("\n"),
                        ].join("\n"),
                    },
                ],
            };
        },
    },
    // 36. renpy_build_project
    {
        name: "renpy_build_project",
        description: "Build/compile a Ren'Py project using the Ren'Py launcher CLI.",
        inputSchema: zod_1.z.object({
            renpy_executable: zod_1.z
                .string()
                .describe("Path to renpy.sh or renpy.exe"),
            project_dir: zod_1.z.string().describe("Path to the project root"),
            target: zod_1.z
                .enum(["lint", "compile", "distribute"])
                .default("compile")
                .describe("Build target"),
        }),
        handler: async (args) => {
            const targetFlag = args.target === "lint"
                ? "lint"
                : args.target === "distribute"
                    ? "distribute"
                    : "compile";
            return new Promise((resolve) => {
                child_process.exec(`"${args.renpy_executable}" "${args.project_dir}" ${targetFlag}`, { timeout: 120000 }, (error, stdout, stderr) => {
                    const output = [
                        `Target: ${targetFlag}`,
                        `Exit code: ${error?.code ?? 0}`,
                        ``,
                        `STDOUT:`,
                        stdout || "(none)",
                        ``,
                        `STDERR:`,
                        stderr || "(none)",
                    ].join("\n");
                    resolve({
                        content: [{ type: "text", text: output }],
                    });
                });
            });
        },
    },
    // 37. renpy_list_assets
    {
        name: "renpy_list_assets",
        description: "List all game assets (images, audio, fonts) in a project directory.",
        inputSchema: zod_1.z.object({
            game_dir: zod_1.z.string().describe("Path to the game/ directory"),
            type: zod_1.z
                .enum(["images", "audio", "fonts", "all"])
                .optional()
                .default("all")
                .describe("Asset type filter"),
        }),
        handler: async (args) => {
            const extensions = {
                images: [".png", ".jpg", ".jpeg", ".webp", ".gif"],
                audio: [".ogg", ".mp3", ".wav", ".opus"],
                fonts: [".ttf", ".otf"],
            };
            const exts = args.type === "all"
                ? Object.values(extensions).flat()
                : extensions[args.type] ?? [];
            const walkDir = (dir) => {
                if (!fs.existsSync(dir))
                    return [];
                const results = [];
                const entries = fs.readdirSync(dir, { withFileTypes: true });
                for (const entry of entries) {
                    const full = path.join(dir, entry.name);
                    if (entry.isDirectory()) {
                        results.push(...walkDir(full));
                    }
                    else if (exts.some((e) => entry.name.endsWith(e))) {
                        results.push(full);
                    }
                }
                return results;
            };
            const assets = walkDir(args.game_dir);
            const byType = {};
            for (const asset of assets) {
                const ext = path.extname(asset).toLowerCase();
                const category = Object.entries(extensions).find(([, exts]) => exts.includes(ext))?.[0] ??
                    "other";
                if (!byType[category])
                    byType[category] = [];
                byType[category].push(asset.replace(args.game_dir, "").replace(/\\/g, "/"));
            }
            return {
                content: [
                    {
                        type: "text",
                        text: `Found ${assets.length} assets:\n\n${JSON.stringify(byType, null, 2)}`,
                    },
                ],
            };
        },
    },
    // 38. renpy_generate_flowchart
    {
        name: "renpy_generate_flowchart",
        description: "Generate a Graphviz DOT flowchart from all .rpy scripts in a directory.",
        inputSchema: zod_1.z.object({
            scripts_dir: zod_1.z.string().describe("Directory containing .rpy files"),
            output_dot: zod_1.z
                .string()
                .optional()
                .describe("Output path for .dot file"),
            output_json: zod_1.z
                .string()
                .optional()
                .describe("Output path for JSON node data"),
        }),
        handler: async (args) => {
            const entries = fs.readdirSync(args.scripts_dir, { recursive: true });
            const rpyFiles = entries
                .filter((e) => e.endsWith(".rpy"))
                .map((e) => path.join(args.scripts_dir, e));
            const allScript = rpyFiles
                .map((f) => fs.readFileSync(f, "utf-8"))
                .join("\n\n");
            const nodes = (0, renpy_generator_js_1.parseFlowchart)(allScript);
            const dot = (0, renpy_generator_js_1.renderFlowchartDot)(nodes);
            if (args.output_dot) {
                fs.writeFileSync(args.output_dot, dot, "utf-8");
            }
            if (args.output_json) {
                fs.writeFileSync(args.output_json, JSON.stringify(nodes, null, 2), "utf-8");
            }
            return {
                content: [
                    {
                        type: "text",
                        text: [
                            `Flowchart generated from ${rpyFiles.length} files`,
                            `Nodes: ${nodes.length}`,
                            args.output_dot ? `DOT: ${args.output_dot}` : "",
                            args.output_json ? `JSON: ${args.output_json}` : "",
                            ``,
                            `Preview (first 50 lines):`,
                            dot.split("\n").slice(0, 50).join("\n"),
                        ]
                            .filter(Boolean)
                            .join("\n"),
                    },
                ],
            };
        },
    },
    // 39. renpy_export_translation
    {
        name: "renpy_export_translation",
        description: "Export all dialogue strings to a JSON translation template file.",
        inputSchema: zod_1.z.object({
            scripts_dir: zod_1.z.string().describe("Directory containing .rpy files"),
            output_path: zod_1.z.string().describe("Output .json path for translation"),
            language: zod_1.z
                .string()
                .optional()
                .default("english")
                .describe("Target language identifier"),
        }),
        handler: async (args) => {
            const entries = fs.readdirSync(args.scripts_dir, { recursive: true });
            const rpyFiles = entries
                .filter((e) => e.endsWith(".rpy"))
                .map((e) => path.join(args.scripts_dir, e));
            const translations = {};
            const dialogueRe = /^\s+\w+\s+"([^"]+)"/gm;
            const narratorRe = /^\s+"([^"]+)"/gm;
            for (const file of rpyFiles) {
                const script = fs.readFileSync(file, "utf-8");
                let m;
                const dr = new RegExp(dialogueRe.source, dialogueRe.flags);
                while ((m = dr.exec(script)) !== null) {
                    if (!m[1].startsWith("##"))
                        translations[m[1]] = m[1];
                }
                const nr = new RegExp(narratorRe.source, narratorRe.flags);
                while ((m = nr.exec(script)) !== null) {
                    if (!m[1].startsWith("##"))
                        translations[m[1]] = m[1];
                }
            }
            const output = {
                language: args.language,
                strings: translations,
                count: Object.keys(translations).length,
            };
            fs.mkdirSync(path.dirname(args.output_path), { recursive: true });
            fs.writeFileSync(args.output_path, JSON.stringify(output, null, 2), "utf-8");
            return {
                content: [
                    {
                        type: "text",
                        text: `Exported ${output.count} strings to ${args.output_path}`,
                    },
                ],
            };
        },
    },
    // 40. renpy_create_gui_customization
    {
        name: "renpy_create_gui_customization",
        description: "Generate a GUI customization block (colors, fonts, layout) for gui.rpy.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Path to gui.rpy"),
            accent_color: zod_1.z
                .string()
                .default("#c8a0ff")
                .describe("Primary accent color"),
            foreground_color: zod_1.z.string().default("#ffffff").describe("Text color"),
            background_color: zod_1.z.string().default("#1a0a2e").describe("Background color"),
            hover_color: zod_1.z
                .string()
                .default("#ff80b4")
                .describe("Hover/highlight color"),
            font: zod_1.z
                .string()
                .optional()
                .describe("Path to custom font file"),
            name_font: zod_1.z
                .string()
                .optional()
                .describe("Path to character name font"),
        }),
        handler: async (args) => {
            const lines = [
                `## GUI Customization — EoBQ Theme`,
                `define gui.accent_color = "${args.accent_color}"`,
                `define gui.idle_color = "${args.foreground_color}"`,
                `define gui.hover_color = "${args.hover_color}"`,
                `define gui.selected_color = "${args.hover_color}"`,
                `define gui.insensitive_color = "#4a3a5a"`,
                `define gui.muted_color = "#4a3a5a"`,
                `define gui.hover_muted_color = "${args.hover_color}88"`,
                `define gui.text_color = "${args.foreground_color}"`,
                `define gui.interface_text_color = "${args.foreground_color}"`,
                `define gui.background = "${args.background_color}"`,
                args.font ? `define gui.default_font = "${args.font}"` : null,
                args.name_font ? `define gui.name_text_font = "${args.name_font}"` : null,
            ]
                .filter(Boolean)
                .join("\n");
            let existing = fs.existsSync(args.file_path)
                ? fs.readFileSync(args.file_path, "utf-8")
                : "";
            fs.mkdirSync(path.dirname(args.file_path), { recursive: true });
            fs.writeFileSync(args.file_path, existing + "\n\n" + lines + "\n", "utf-8");
            return { content: [{ type: "text", text: `GUI theme applied:\n${lines}` }] };
        },
    },
    // 41. renpy_add_achievement
    {
        name: "renpy_add_achievement",
        description: "Add an achievement definition to the achievements .rpy file.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Path to achievements .rpy file"),
            id: zod_1.z.string().describe("Achievement ID (snake_case)"),
            name: zod_1.z.string().describe("Display name"),
            description: zod_1.z.string().describe("Achievement description"),
            icon: zod_1.z.string().optional().describe("Icon image path"),
            points: zod_1.z.number().optional().describe("Points value"),
        }),
        handler: async (args) => {
            const code = (0, renpy_generator_js_1.generateAchievement)(args.id, args.name, args.description, args.icon, args.points);
            let existing = fs.existsSync(args.file_path)
                ? fs.readFileSync(args.file_path, "utf-8")
                : `## Achievements\n\n`;
            fs.mkdirSync(path.dirname(args.file_path), { recursive: true });
            fs.writeFileSync(args.file_path, existing + "\n" + code + "\n", "utf-8");
            return { content: [{ type: "text", text: `Achievement added:\n${code}` }] };
        },
    },
    // 42. renpy_generate_gallery
    {
        name: "renpy_generate_gallery",
        description: "Generate a gallery screen and unlock tracking for a list of CG entries.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Output .rpy file for gallery"),
            entries: zod_1.z
                .array(zod_1.z.object({
                id: zod_1.z.string(),
                name: zod_1.z.string(),
                image: zod_1.z.string(),
                unlock_condition: zod_1.z.string(),
                thumbnail: zod_1.z.string().optional(),
            }))
                .describe("Gallery CG entries"),
        }),
        handler: async (args) => {
            const lines = [
                `## CG Gallery — EoBQ`,
                `## Generated by mcp-renpy`,
                ``,
                `init python:`,
                `    gallery = Gallery()`,
                ``,
            ];
            for (const entry of args.entries) {
                lines.push((0, renpy_generator_js_1.generateGalleryEntry)(entry.id, entry.name, entry.image, entry.unlock_condition, entry.thumbnail));
                lines.push(``);
            }
            // Gallery screen
            lines.push(`screen gallery_screen():`);
            lines.push(`    tag menu`);
            lines.push(`    use game_menu(_("Gallery"), scroll="viewport"):`);
            lines.push(`        grid ${Math.min(4, args.entries.length)} ${Math.ceil(args.entries.length / 4)}:`);
            lines.push(`            spacing 10`);
            for (const entry of args.entries) {
                lines.push(`            ## Gallery button: ${entry.name}`);
                lines.push(`            add gallery.make_button("${entry.id}", "images/gallery/thumb_${entry.id}.png")`);
            }
            const content = lines.join("\n");
            fs.mkdirSync(path.dirname(args.file_path), { recursive: true });
            fs.writeFileSync(args.file_path, content, "utf-8");
            return {
                content: [
                    {
                        type: "text",
                        text: `Gallery generated at ${args.file_path}\n${args.entries.length} entries`,
                    },
                ],
            };
        },
    },
];
//# sourceMappingURL=project-tools.js.map