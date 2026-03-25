"use strict";
// ============================================================
// Scene Building Tools (8 tools)
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
exports.sceneToolDefs = void 0;
const zod_1 = require("zod");
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const renpy_generator_js_1 = require("../renpy-generator.js");
exports.sceneToolDefs = [
    // 19. renpy_create_scene
    {
        name: "renpy_create_scene",
        description: "Create a complete scene block: background, music, character entry, and initial dialogue stub.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Output .rpy file path"),
            label: zod_1.z.string().describe("Scene label name"),
            background: zod_1.z.string().describe("Background image name"),
            music: zod_1.z.string().optional().describe("Background music file"),
            characters: zod_1.z
                .array(zod_1.z.string())
                .optional()
                .default([])
                .describe("Characters to show (image tags)"),
            transition: zod_1.z
                .string()
                .optional()
                .default("dissolve")
                .describe("Scene entry transition"),
        }),
        handler: async (args) => {
            const lines = [
                `label ${args.label}:`,
                `    ${(0, renpy_generator_js_1.generateScene)(args.background, args.transition)}`,
            ];
            if (args.music) {
                lines.push(`    ${(0, renpy_generator_js_1.generatePlayMusic)(args.music, 1.0, 1.0)}`);
            }
            for (const char of args.characters) {
                lines.push(`    ${(0, renpy_generator_js_1.generateShow)(char, "center", "dissolve")}`);
            }
            lines.push(`    "## Scene ${args.label} — placeholder dialogue"`);
            lines.push(`    return`);
            lines.push(``);
            const content = lines.join("\n");
            let existing = fs.existsSync(args.file_path)
                ? fs.readFileSync(args.file_path, "utf-8")
                : (0, renpy_generator_js_1.fileHeader)(`Scene: ${args.label}`);
            fs.mkdirSync(path.dirname(args.file_path), { recursive: true });
            fs.writeFileSync(args.file_path, existing + "\n" + content, "utf-8");
            return { content: [{ type: "text", text: `Scene created:\n${content}` }] };
        },
    },
    // 20. renpy_add_transition
    {
        name: "renpy_add_transition",
        description: "Add a visual transition statement to a .rpy file after a label.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Path to .rpy file"),
            transition: zod_1.z
                .enum([
                "dissolve",
                "fade",
                "blinds",
                "squares",
                "pixellate",
                "wipeleft",
                "wiperight",
                "wipeup",
                "wipedown",
                "flipvertical",
                "fliphorizontal",
            ])
                .describe("Transition type"),
            after_label: zod_1.z.string().optional().describe("Insert after this label"),
            custom_time: zod_1.z.number().optional().describe("Custom duration in seconds"),
        }),
        handler: async (args) => {
            let script = fs.readFileSync(args.file_path, "utf-8");
            const transName = args.custom_time
                ? `${args.transition}(${args.custom_time})`
                : args.transition;
            const line = `    ${(0, renpy_generator_js_1.generateTransition)(transName)}`;
            if (args.after_label) {
                const re = new RegExp(`(label\\s+${args.after_label}\\s*:[^\\n]*)`);
                script = script.replace(re, `$1\n${line}`);
            }
            else {
                script = script.trimEnd() + "\n" + line + "\n";
            }
            fs.writeFileSync(args.file_path, script, "utf-8");
            return { content: [{ type: "text", text: `Added transition: ${transName}` }] };
        },
    },
    // 21. renpy_add_show
    {
        name: "renpy_add_show",
        description: "Add a show or hide statement for a character or image.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Path to .rpy file"),
            action: zod_1.z.enum(["show", "hide"]).describe("Whether to show or hide"),
            image: zod_1.z.string().describe("Image or character tag"),
            at: zod_1.z.string().optional().describe("Position/transform (e.g. 'left', 'center')"),
            transition: zod_1.z.string().optional().describe("Transition name"),
            after_label: zod_1.z.string().optional().describe("Insert after this label"),
        }),
        handler: async (args) => {
            let script = fs.readFileSync(args.file_path, "utf-8");
            const line = args.action === "show"
                ? `    ${(0, renpy_generator_js_1.generateShow)(args.image, args.at, args.transition)}`
                : `    ${(0, renpy_generator_js_1.generateHide)(args.image, args.transition)}`;
            if (args.after_label) {
                const re = new RegExp(`(label\\s+${args.after_label}\\s*:[^\\n]*)`);
                script = script.replace(re, `$1\n${line}`);
            }
            else {
                script = script.trimEnd() + "\n" + line + "\n";
            }
            fs.writeFileSync(args.file_path, script, "utf-8");
            return { content: [{ type: "text", text: `Added: ${line.trim()}` }] };
        },
    },
    // 22. renpy_add_animation
    {
        name: "renpy_add_animation",
        description: "Add an ATL animation transform to a .rpy file.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Path to .rpy file"),
            name: zod_1.z.string().describe("Transform name"),
            frames: zod_1.z
                .array(zod_1.z.object({
                image: zod_1.z.string(),
                delay: zod_1.z.number(),
            }))
                .describe("Animation frames with image paths and delays"),
        }),
        handler: async (args) => {
            const code = (0, renpy_generator_js_1.generateATLAnimation)(args.name, args.frames);
            let existing = fs.existsSync(args.file_path)
                ? fs.readFileSync(args.file_path, "utf-8")
                : "";
            fs.writeFileSync(args.file_path, existing + "\n" + code + "\n", "utf-8");
            return { content: [{ type: "text", text: `Added animation:\n${code}` }] };
        },
    },
    // 23. renpy_set_music
    {
        name: "renpy_set_music",
        description: "Append a music play/stop statement to a .rpy label.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Path to .rpy file"),
            file: zod_1.z.string().describe("Audio file path (or 'stop' to stop music)"),
            fadeout: zod_1.z.number().optional().describe("Fadeout duration in seconds"),
            fadein: zod_1.z.number().optional().describe("Fadein duration in seconds"),
            channel: zod_1.z
                .enum(["music", "ambient", "voice"])
                .optional()
                .default("music")
                .describe("Audio channel"),
        }),
        handler: async (args) => {
            let line;
            if (args.file === "stop") {
                const fout = args.fadeout ? ` fadeout ${args.fadeout}` : "";
                line = `    stop ${args.channel}${fout}`;
            }
            else {
                const fout = args.fadeout ? ` fadeout ${args.fadeout}` : "";
                const fin = args.fadein ? ` fadein ${args.fadein}` : "";
                line = `    play ${args.channel} "${args.file}"${fout}${fin}`;
            }
            let script = fs.readFileSync(args.file_path, "utf-8");
            script = script.trimEnd() + "\n" + line + "\n";
            fs.writeFileSync(args.file_path, script, "utf-8");
            return { content: [{ type: "text", text: `Set music:\n${line}` }] };
        },
    },
    // 24. renpy_add_sound_effect
    {
        name: "renpy_add_sound_effect",
        description: "Add a sound effect play statement to a .rpy file.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Path to .rpy file"),
            sound_file: zod_1.z.string().describe("Sound file path"),
            channel: zod_1.z
                .string()
                .optional()
                .default("sound")
                .describe("Channel name"),
            after_label: zod_1.z.string().optional().describe("Insert after this label"),
        }),
        handler: async (args) => {
            let script = fs.readFileSync(args.file_path, "utf-8");
            const line = `    ${(0, renpy_generator_js_1.generatePlaySound)(args.sound_file, args.channel)}`;
            if (args.after_label) {
                const re = new RegExp(`(label\\s+${args.after_label}\\s*:[^\\n]*)`);
                script = script.replace(re, `$1\n${line}`);
            }
            else {
                script = script.trimEnd() + "\n" + line + "\n";
            }
            fs.writeFileSync(args.file_path, script, "utf-8");
            return { content: [{ type: "text", text: `Added SFX:\n${line}` }] };
        },
    },
    // 25. renpy_create_cg_scene
    {
        name: "renpy_create_cg_scene",
        description: "Create a CG gallery scene with unlock tracking and viewer label.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Output .rpy file path"),
            cg_id: zod_1.z.string().describe("CG identifier (e.g. 'aria_cg01')"),
            cg_image: zod_1.z.string().describe("Image path for the CG"),
            unlock_condition: zod_1.z.string().describe("Python condition string to unlock"),
            background_music: zod_1.z.string().optional().describe("Music during CG"),
            caption: zod_1.z.string().optional().describe("Caption text shown below CG"),
        }),
        handler: async (args) => {
            const lines = [
                `## CG Scene: ${args.cg_id}`,
                `image ${args.cg_id} = "${args.cg_image}"`,
                ``,
                `label cg_view_${args.cg_id}:`,
                `    scene black with dissolve`,
                args.background_music
                    ? `    play music "${args.background_music}" fadein 1.5`
                    : `    ## no music`,
                `    pause 0.5`,
                `    show ${args.cg_id} with dissolve`,
                args.caption ? `    "## Caption: ${args.caption}"` : `    pause 2.0`,
                `    hide ${args.cg_id} with dissolve`,
                `    return`,
                ``,
                `## Gallery unlock check`,
                `label cg_unlock_${args.cg_id}:`,
                `    if ${args.unlock_condition}:`,
                `        $ persistent.cg_${args.cg_id}_unlocked = True`,
                `    return`,
            ];
            const content = lines.join("\n");
            let existing = fs.existsSync(args.file_path)
                ? fs.readFileSync(args.file_path, "utf-8")
                : "";
            fs.mkdirSync(path.dirname(args.file_path), { recursive: true });
            fs.writeFileSync(args.file_path, existing + "\n" + content + "\n", "utf-8");
            return { content: [{ type: "text", text: `CG scene created:\n${content}` }] };
        },
    },
    // 26. renpy_create_h_scene
    {
        name: "renpy_create_h_scene",
        description: "Create an adult scene scaffold with intensity level and SoulForge DNA parameters.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Output .rpy file path"),
            label: zod_1.z.string().describe("Scene label"),
            character_id: zod_1.z.string().describe("Character variable name"),
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
            intensity: zod_1.z
                .enum(["soft", "medium", "explicit", "extreme"])
                .describe("Scene intensity level"),
            corruption_stage: zod_1.z.number().min(1).max(5).describe("Corruption stage (1-5)"),
            acts: zod_1.z
                .array(zod_1.z.object({
                id: zod_1.z.string(),
                description: zod_1.z.string(),
                dialogue_count: zod_1.z.number(),
                has_cg: zod_1.z.boolean(),
            }))
                .describe("Scene acts"),
            unlock_condition: zod_1.z.string().optional().describe("Python condition to unlock"),
            cg_prefix: zod_1.z.string().optional().describe("CG image name prefix"),
        }),
        handler: async (args) => {
            const cfg = {
                label: args.label,
                character_id: args.character_id,
                dna: args.dna,
                intensity: args.intensity,
                corruption_stage: args.corruption_stage,
                acts: args.acts,
                unlock_condition: args.unlock_condition,
                cg_prefix: args.cg_prefix,
            };
            const code = (0, renpy_generator_js_1.generateHScene)(cfg);
            let existing = fs.existsSync(args.file_path)
                ? fs.readFileSync(args.file_path, "utf-8")
                : "";
            fs.mkdirSync(path.dirname(args.file_path), { recursive: true });
            fs.writeFileSync(args.file_path, existing + "\n" + code + "\n", "utf-8");
            return { content: [{ type: "text", text: `H-scene scaffold created:\n${code}` }] };
        },
    },
];
//# sourceMappingURL=scene-tools.js.map