"use strict";
// ============================================================
// EoBQ-Specific Tools (8 tools)
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
exports.eoqToolDefs = void 0;
const zod_1 = require("zod");
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const renpy_generator_js_1 = require("../renpy-generator.js");
// ── EoBQ Queen archetypes ──────────────────────────────────────
const QUEEN_ARCHETYPES = {
    ice_queen: {
        archetype: "ice_queen",
        corruption_vector: "thawed_obsession",
        voice_style: "cold_formal",
        affinity_type: "slow_burn",
    },
    fire_dancer: {
        archetype: "fire_dancer",
        corruption_vector: "uncontrolled_passion",
        voice_style: "breathy_intimate",
        affinity_type: "volatile",
    },
    corrupted_saint: {
        archetype: "corrupted_saint",
        corruption_vector: "guilt_spiral",
        voice_style: "pleading_broken",
        affinity_type: "obsession",
    },
    dark_empress: {
        archetype: "dark_empress",
        corruption_vector: "power_hunger",
        voice_style: "commanding_seductive",
        affinity_type: "dominance",
    },
    fallen_angel: {
        archetype: "fallen_angel",
        corruption_vector: "grief",
        voice_style: "ethereal_hollow",
        affinity_type: "salvation",
    },
    cursed_oracle: {
        archetype: "cursed_oracle",
        corruption_vector: "fate_despair",
        voice_style: "fragmented_cryptic",
        affinity_type: "doom",
    },
};
exports.eoqToolDefs = [
    // 43. eoq_create_queen_route
    {
        name: "eoq_create_queen_route",
        description: "Create a complete queen route with DNA integration, acts, affinity tracking, and ending stubs.",
        inputSchema: zod_1.z.object({
            output_dir: zod_1.z
                .string()
                .describe("Directory to write the route files into"),
            queen_id: zod_1.z.string().describe("Queen identifier (snake_case, e.g. 'seraphina')"),
            queen_name: zod_1.z.string().describe("Display name"),
            archetype: zod_1.z
                .enum([
                "ice_queen",
                "fire_dancer",
                "corrupted_saint",
                "dark_empress",
                "fallen_angel",
                "cursed_oracle",
            ])
                .describe("Queen archetype"),
            color_hex: zod_1.z.string().describe("Name color hex"),
            kink_profile: zod_1.z
                .array(zod_1.z.string())
                .describe("Kink/trait profile from SoulForge DNA"),
            acts: zod_1.z.number().min(1).max(5).default(3).describe("Number of acts"),
            scenes_per_act: zod_1.z.number().min(2).max(10).default(4),
        }),
        handler: async (args) => {
            const archetypeDefaults = QUEEN_ARCHETYPES[args.archetype] ?? {};
            const dna = {
                name: args.queen_name,
                archetype: args.archetype,
                affinity_type: archetypeDefaults.affinity_type ?? "standard",
                corruption_vector: archetypeDefaults.corruption_vector ?? "unknown",
                kink_profile: args.kink_profile,
                voice_style: archetypeDefaults.voice_style ?? "neutral",
                color_hex: args.color_hex,
                sprite_style: args.archetype,
            };
            fs.mkdirSync(args.output_dir, { recursive: true });
            const files = [];
            // 1. Character definition
            const charFile = path.join(args.output_dir, `${args.queen_id}_character.rpy`);
            const charCode = (0, renpy_generator_js_1.fileHeader)(`Character: ${args.queen_name}`) +
                "\n" +
                (0, renpy_generator_js_1.generateCharacterFromDNA)(dna);
            fs.writeFileSync(charFile, charCode, "utf-8");
            files.push(charFile);
            // 2. Affinity & variables
            const varFile = path.join(args.output_dir, `${args.queen_id}_variables.rpy`);
            const varLines = [
                `## Variables: ${args.queen_name}`,
                `default ${args.queen_id}_affinity = 0`,
                `default ${args.queen_id}_corruption = 0`,
                `default ${args.queen_id}_route_active = False`,
                `default ${args.queen_id}_route_complete = False`,
                `define ${args.queen_id}_route_unlock_threshold = 30`,
            ].join("\n");
            fs.writeFileSync(varFile, varLines, "utf-8");
            files.push(varFile);
            // 3. Route script
            const routeFile = path.join(args.output_dir, `${args.queen_id}_route.rpy`);
            const routeLines = [
                (0, renpy_generator_js_1.fileHeader)(`Route: ${args.queen_name} — ${args.archetype}`),
                `label ${args.queen_id}_route_start:`,
                `    $ ${args.queen_id}_route_active = True`,
                `    jump ${args.queen_id}_act1_scene1`,
                ``,
            ];
            for (let act = 1; act <= args.acts; act++) {
                routeLines.push(`## ═══ Act ${act} ═══`);
                for (let scene = 1; scene <= args.scenes_per_act; scene++) {
                    const label = `${args.queen_id}_act${act}_scene${scene}`;
                    const next = scene < args.scenes_per_act
                        ? `${args.queen_id}_act${act}_scene${scene + 1}`
                        : act < args.acts
                            ? `${args.queen_id}_act${act + 1}_scene1`
                            : `${args.queen_id}_route_end`;
                    routeLines.push(`label ${label}:`);
                    routeLines.push(`    ## [${args.archetype}] Act ${act} Scene ${scene}`);
                    routeLines.push(`    ## DNA: corruption_vector=${dna.corruption_vector} | voice=${dna.voice_style}`);
                    routeLines.push(`    "## Placeholder — fill with generated content"`);
                    routeLines.push(`    jump ${next}`);
                    routeLines.push(``);
                }
            }
            routeLines.push(`label ${args.queen_id}_route_end:`);
            routeLines.push(`    $ ${args.queen_id}_route_complete = True`);
            routeLines.push(`    ## Route complete — trigger ending check`);
            routeLines.push(`    jump ${args.queen_id}_ending_check`);
            routeLines.push(``);
            routeLines.push(`label ${args.queen_id}_ending_check:`);
            routeLines.push(`    if ${args.queen_id}_affinity >= 80:`);
            routeLines.push(`        jump ${args.queen_id}_ending_true_love`);
            routeLines.push(`    elif ${args.queen_id}_corruption >= 4:`);
            routeLines.push(`        jump ${args.queen_id}_ending_corruption_complete`);
            routeLines.push(`    else:`);
            routeLines.push(`        jump ${args.queen_id}_ending_bad_end`);
            routeLines.push(``);
            routeLines.push(`label ${args.queen_id}_ending_true_love:`);
            routeLines.push(`    ## TODO: True love ending`);
            routeLines.push(`    return`);
            routeLines.push(``);
            routeLines.push(`label ${args.queen_id}_ending_corruption_complete:`);
            routeLines.push(`    ## TODO: Corruption complete ending`);
            routeLines.push(`    return`);
            routeLines.push(``);
            routeLines.push(`label ${args.queen_id}_ending_bad_end:`);
            routeLines.push(`    ## TODO: Bad end`);
            routeLines.push(`    return`);
            fs.writeFileSync(routeFile, routeLines.join("\n"), "utf-8");
            files.push(routeFile);
            return {
                content: [
                    {
                        type: "text",
                        text: [
                            `Queen route created for: ${args.queen_name}`,
                            `Archetype: ${args.archetype}`,
                            `Acts: ${args.acts} × ${args.scenes_per_act} scenes = ${args.acts * args.scenes_per_act} labels`,
                            ``,
                            `Files created:`,
                            ...files.map((f) => `  ${f}`),
                        ].join("\n"),
                    },
                ],
            };
        },
    },
    // 44. eoq_generate_corruption_arc
    {
        name: "eoq_generate_corruption_arc",
        description: "Generate a 5-stage corruption progression arc for a queen, with scene stubs.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Output .rpy file path"),
            queen_id: zod_1.z.string().describe("Queen identifier"),
            queen_name: zod_1.z.string().describe("Display name"),
            corruption_vector: zod_1.z.string().describe("Primary corruption driver"),
            stage_descriptions: zod_1.z
                .array(zod_1.z.string())
                .length(5)
                .describe("Description for each of the 5 stages"),
            intensities: zod_1.z
                .array(zod_1.z.enum(["soft", "medium", "explicit", "extreme"]))
                .length(5)
                .describe("Intensity for each stage"),
        }),
        handler: async (args) => {
            const stages = args.stage_descriptions.map((desc, i) => ({
                stage: i + 1,
                label: `${args.queen_id}_corrupt_stage${i + 1}`,
                description: desc,
                trigger_condition: `${args.queen_id}_corruption == ${i}`,
                scene_type: i < 2 ? "dialogue" : i < 4 ? "event" : "h_scene",
                intensity: args.intensities[i],
            }));
            const code = (0, renpy_generator_js_1.fileHeader)(`Corruption Arc: ${args.queen_name} — vector: ${args.corruption_vector}`) +
                "\n" +
                (0, renpy_generator_js_1.generateCorruptionArc)(args.queen_id, stages);
            fs.mkdirSync(path.dirname(args.file_path), { recursive: true });
            fs.writeFileSync(args.file_path, code, "utf-8");
            return {
                content: [
                    {
                        type: "text",
                        text: `Corruption arc created at ${args.file_path}\n5 stages, vector: ${args.corruption_vector}`,
                    },
                ],
            };
        },
    },
    // 45. eoq_create_council_scene
    {
        name: "eoq_create_council_scene",
        description: "Create a Council of Queens political scene with queens present, agenda, and player choice impact.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Output .rpy file path"),
            label: zod_1.z.string().describe("Scene label"),
            queens_present: zod_1.z
                .array(zod_1.z.string())
                .describe("List of queen IDs in the scene"),
            agenda: zod_1.z
                .string()
                .describe("Political agenda/topic of the council session"),
            player_choices: zod_1.z
                .array(zod_1.z.object({
                text: zod_1.z.string(),
                jump: zod_1.z.string().optional(),
                affinity_delta: zod_1.z.record(zod_1.z.number()).optional(),
            }))
                .describe("Player choice options"),
            tension_level: zod_1.z
                .number()
                .min(1)
                .max(5)
                .describe("Political tension level (1-5)"),
            background: zod_1.z
                .string()
                .optional()
                .default("bg_throne_room")
                .describe("Background image"),
            music: zod_1.z
                .string()
                .optional()
                .default("audio/music/council_theme.ogg")
                .describe("Council music"),
        }),
        handler: async (args) => {
            const lines = [
                (0, renpy_generator_js_1.fileHeader)(`Council Scene: ${args.label}`),
                ``,
                `label ${args.label}:`,
                `    ## Council of Queens — Tension: ${args.tension_level}/5`,
                `    ## Agenda: ${args.agenda}`,
                `    ## Queens: ${args.queens_present.join(", ")}`,
                `    scene ${args.background} with dissolve`,
                `    play music "${args.music}" fadein 2.0`,
                ``,
            ];
            // Show all queens
            const positions = ["left", "center", "right", "far left", "far right"];
            args.queens_present.forEach((q, i) => {
                const pos = positions[i % positions.length];
                lines.push(`    show ${q} at ${pos.replace(" ", "_")} with dissolve`);
            });
            lines.push(`    ## Council opening narration placeholder`);
            lines.push(`    "## The Council of Queens convenes..."`);
            lines.push(``);
            // Queen dialogue stubs
            for (const q of args.queens_present) {
                lines.push(`    ${q} "## [${q}] Council dialogue placeholder"`);
            }
            lines.push(``);
            // Player choice
            const menuBlock = (0, renpy_generator_js_1.generateChoiceMenu)(`How do you respond to the council's deliberation?`, args.player_choices);
            lines.push(menuBlock
                .split("\n")
                .map((l) => `    ${l}`)
                .join("\n"));
            lines.push(``);
            lines.push(`    return`);
            const content = lines.join("\n");
            fs.mkdirSync(path.dirname(args.file_path), { recursive: true });
            fs.writeFileSync(args.file_path, content, "utf-8");
            return {
                content: [
                    {
                        type: "text",
                        text: `Council scene created at ${args.file_path}\nQueens: ${args.queens_present.join(", ")}\nTension: ${args.tension_level}/5`,
                    },
                ],
            };
        },
    },
    // 46. eoq_generate_awakening_event
    {
        name: "eoq_generate_awakening_event",
        description: "Generate an Awakening event sequence — when a queen's dormant power/memory manifests.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Output .rpy file path"),
            queen_id: zod_1.z.string().describe("Queen identifier"),
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
            trigger: zod_1.z.string().describe("What triggers the awakening"),
            manifestation_type: zod_1.z
                .enum(["power", "memory", "vision", "possession"])
                .describe("Type of awakening manifestation"),
            scene_count: zod_1.z
                .number()
                .min(1)
                .max(5)
                .default(3)
                .describe("Number of awakening scenes"),
        }),
        handler: async (args) => {
            const lines = [
                (0, renpy_generator_js_1.fileHeader)(`Awakening Event: ${args.dna.name} — ${args.manifestation_type}`),
                ``,
                `## Trigger: ${args.trigger}`,
                ``,
                `label ${args.queen_id}_awakening:`,
                `    ## Awakening: ${args.manifestation_type}`,
                `    ## DNA archetype: ${args.dna.archetype} | vector: ${args.dna.corruption_vector}`,
                `    scene black with dissolve`,
                `    play music "audio/music/awakening_theme.ogg" fadein 2.0`,
                ``,
            ];
            for (let i = 1; i <= args.scene_count; i++) {
                lines.push(`    ## Awakening scene ${i}/${args.scene_count}`);
                lines.push(`    show ${args.queen_id} dream at center with dissolve`);
                lines.push(`    ${args.queen_id} "## [${args.dna.voice_style}] Awakening dialogue ${i}"`);
                lines.push(`    "## Narration: awakening ${i}"`);
                lines.push(``);
            }
            lines.push(`    ## Awakening resolves`);
            lines.push(`    $ ${args.queen_id}_awakening_complete = True`);
            lines.push(`    $ ${args.queen_id}_corruption += 1  ## Awakening increases corruption`);
            lines.push(`    return`);
            const content = lines.join("\n");
            fs.mkdirSync(path.dirname(args.file_path), { recursive: true });
            fs.writeFileSync(args.file_path, content, "utf-8");
            return {
                content: [
                    {
                        type: "text",
                        text: `Awakening event created at ${args.file_path}\nType: ${args.manifestation_type} | Scenes: ${args.scene_count}`,
                    },
                ],
            };
        },
    },
    // 47. eoq_create_harem_wars_event
    {
        name: "eoq_create_harem_wars_event",
        description: "Generate a jealousy/rivalry event between two queens with player mediation choices.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Output .rpy file path"),
            label: zod_1.z.string().describe("Event label"),
            instigator: zod_1.z
                .string()
                .describe("Queen ID of the jealous/aggressive party"),
            target: zod_1.z.string().describe("Queen ID of the target"),
            rivalry_type: zod_1.z
                .enum(["jealousy", "dominance", "alliance_break", "sabotage"])
                .describe("Type of rivalry event"),
            player_side_choices: zod_1.z
                .array(zod_1.z.object({
                text: zod_1.z.string(),
                favors: zod_1.z.string().describe("Which queen this choice favors"),
                affinity_delta: zod_1.z.record(zod_1.z.number()).optional(),
            }))
                .describe("Player side-taking choices"),
        }),
        handler: async (args) => {
            const lines = [
                (0, renpy_generator_js_1.fileHeader)(`Harem Wars Event: ${args.instigator} vs ${args.target} — ${args.rivalry_type}`),
                ``,
                `label ${args.label}:`,
                `    ## Rivalry type: ${args.rivalry_type}`,
                `    ## ${args.instigator} vs ${args.target}`,
                `    scene bg_corridor with dissolve`,
                ``,
                `    show ${args.instigator} at left with dissolve`,
                `    show ${args.target} at right with dissolve`,
                ``,
                `    ## Confrontation opening`,
                `    ${args.instigator} "## [instigator] Opening line placeholder"`,
                `    ${args.target} "## [target] Response placeholder"`,
                `    ${args.instigator} "## [instigator] Escalation placeholder"`,
                ``,
                `    "## The tension between them is palpable..."`,
                ``,
            ];
            // Player choice
            const choices = args.player_side_choices.map((c) => ({
                text: c.text,
                jump: `${args.label}_choice_${c.favors}`,
                affinity_delta: c.affinity_delta,
            }));
            const menuBlock = (0, renpy_generator_js_1.generateChoiceMenu)("How do you intervene?", choices);
            lines.push(menuBlock
                .split("\n")
                .map((l) => `    ${l}`)
                .join("\n"));
            lines.push(``);
            // Choice outcomes
            for (const choice of args.player_side_choices) {
                lines.push(`label ${args.label}_choice_${choice.favors}:`);
                lines.push(`    ## Player favors: ${choice.favors}`);
                lines.push(`    ${choice.favors} "## Grateful response placeholder"`);
                const other = choice.favors === args.instigator ? args.target : args.instigator;
                lines.push(`    ${other} "## Resentful response placeholder"`);
                lines.push(`    return`);
                lines.push(``);
            }
            const content = lines.join("\n");
            fs.mkdirSync(path.dirname(args.file_path), { recursive: true });
            fs.writeFileSync(args.file_path, content, "utf-8");
            return {
                content: [
                    {
                        type: "text",
                        text: `Harem Wars event created at ${args.file_path}\n${args.instigator} vs ${args.target}: ${args.rivalry_type}`,
                    },
                ],
            };
        },
    },
    // 48. eoq_generate_phone_messages
    {
        name: "eoq_generate_phone_messages",
        description: "Generate obsession-level phone message sequences from a queen to the player.",
        inputSchema: zod_1.z.object({
            file_path: zod_1.z.string().describe("Output .rpy file path"),
            queen_id: zod_1.z.string().describe("Queen identifier (sender)"),
            messages: zod_1.z
                .array(zod_1.z.object({
                timestamp_label: zod_1.z.string().describe("Label suffix for this message group"),
                messages: zod_1.z.array(zod_1.z.string()).describe("Message texts"),
                attachment: zod_1.z.string().optional().describe("Attached image/file"),
                obsession_level: zod_1.z
                    .number()
                    .min(1)
                    .max(5)
                    .describe("Obsession intensity (1=mild, 5=extreme)"),
            }))
                .describe("Message groups"),
        }),
        handler: async (args) => {
            const enriched = args.messages.map((m) => ({
                ...m,
                sender: args.queen_id,
            }));
            const header = (0, renpy_generator_js_1.fileHeader)(`Phone Messages: ${args.queen_id}`);
            const code = (0, renpy_generator_js_1.generatePhoneMessages)(enriched);
            fs.mkdirSync(path.dirname(args.file_path), { recursive: true });
            fs.writeFileSync(args.file_path, header + "\n" + code, "utf-8");
            return {
                content: [
                    {
                        type: "text",
                        text: `Phone messages written at ${args.file_path}\n${args.messages.length} message groups`,
                    },
                ],
            };
        },
    },
    // 49. eoq_create_stripper_arc
    {
        name: "eoq_create_stripper_arc",
        description: "Create a stripper arc progression for a queen — staged degradation/empowerment arc.",
        inputSchema: zod_1.z.object({
            output_dir: zod_1.z.string().describe("Directory for arc files"),
            queen_id: zod_1.z.string().describe("Queen identifier"),
            queen_name: zod_1.z.string().describe("Display name"),
            venue_name: zod_1.z.string().describe("Club/venue name"),
            stages: zod_1.z.number().min(3).max(7).default(5).describe("Number of arc stages"),
            arc_direction: zod_1.z
                .enum(["degradation", "empowerment", "ambiguous"])
                .describe("Narrative direction of the arc"),
        }),
        handler: async (args) => {
            fs.mkdirSync(args.output_dir, { recursive: true });
            const lines = [
                (0, renpy_generator_js_1.fileHeader)(`Stripper Arc: ${args.queen_name} @ ${args.venue_name} [${args.arc_direction}]`),
                ``,
                `default ${args.queen_id}_stripper_stage = 0`,
                `default ${args.queen_id}_venue_reputation = 0`,
                ``,
            ];
            for (let stage = 1; stage <= args.stages; stage++) {
                const intensity = stage <= 2 ? "soft" : stage <= 3 ? "medium" : stage <= 4 ? "explicit" : "extreme";
                lines.push(`## ─── Stage ${stage}/${args.stages} ───`);
                lines.push(`label ${args.queen_id}_strip_stage${stage}:`);
                lines.push(`    ## Direction: ${args.arc_direction} | Intensity: ${intensity}`);
                lines.push(`    ## Venue: ${args.venue_name}`);
                lines.push(`    scene bg_${args.venue_name.toLowerCase().replace(/\s/g, "_")}_stage with dissolve`);
                lines.push(`    play music "audio/music/club_stage${stage}.ogg" fadein 1.0`);
                lines.push(`    show ${args.queen_id} strip_stage${stage} at center`);
                lines.push(``);
                lines.push(`    ## Internal monologue`);
                lines.push(`    ${args.queen_id} "## [internal] Stage ${stage} monologue — ${args.arc_direction}"`);
                lines.push(`    "## Audience reaction narration"`);
                lines.push(``);
                lines.push(`    $ ${args.queen_id}_stripper_stage = ${stage}`);
                if (stage < args.stages) {
                    lines.push(`    jump ${args.queen_id}_strip_stage${stage}_choice`);
                    lines.push(``);
                    lines.push(`label ${args.queen_id}_strip_stage${stage}_choice:`);
                    lines.push((0, renpy_generator_js_1.generateChoiceMenu)(`Continue the arc?`, [
                        {
                            text: "Push further",
                            jump: `${args.queen_id}_strip_stage${stage + 1}`,
                        },
                        {
                            text: "Pull back tonight",
                            jump: `${args.queen_id}_strip_retreat`,
                        },
                    ])
                        .split("\n")
                        .map((l) => `    ${l}`)
                        .join("\n"));
                }
                else {
                    lines.push(`    jump ${args.queen_id}_strip_finale`);
                }
                lines.push(``);
            }
            lines.push(`label ${args.queen_id}_strip_retreat:`);
            lines.push(`    "## She pulls back for tonight..."`);
            lines.push(`    return`);
            lines.push(``);
            lines.push(`label ${args.queen_id}_strip_finale:`);
            lines.push(`    ## Arc complete`);
            lines.push(`    $ ${args.queen_id}_stripper_arc_complete = True`);
            lines.push(`    return`);
            const filePath = path.join(args.output_dir, `${args.queen_id}_stripper_arc.rpy`);
            fs.writeFileSync(filePath, lines.join("\n"), "utf-8");
            return {
                content: [
                    {
                        type: "text",
                        text: [
                            `Stripper arc created at ${filePath}`,
                            `Queen: ${args.queen_name} | Venue: ${args.venue_name}`,
                            `Stages: ${args.stages} | Direction: ${args.arc_direction}`,
                        ].join("\n"),
                    },
                ],
            };
        },
    },
    // 50. eoq_create_ending_sequence
    {
        name: "eoq_create_ending_sequence",
        description: "Create one of the 8 EoBQ ending types as a full sequence with narration stubs, CG calls, and achievement unlock.",
        inputSchema: zod_1.z.object({
            output_dir: zod_1.z.string().describe("Directory for ending files"),
            queen_id: zod_1.z
                .string()
                .optional()
                .describe("Queen ID if queen-specific ending"),
            ending_type: zod_1.z
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
            title: zod_1.z.string().describe("Ending title"),
            conditions: zod_1.z
                .array(zod_1.z.string())
                .describe("List of conditions that lead to this ending"),
            description: zod_1.z
                .string()
                .describe("Narrative summary of the ending"),
            music: zod_1.z.string().optional().describe("Ending theme music file"),
            cg: zod_1.z.string().optional().describe("Ending CG image name"),
        }),
        handler: async (args) => {
            const prefix = args.queen_id ? `${args.queen_id}_` : "";
            const label = `${prefix}ending_${args.ending_type}`;
            const cfg = {
                type: args.ending_type,
                label,
                conditions: args.conditions,
                title: args.title,
                music: args.music,
                cg: args.cg,
                description: args.description,
            };
            const code = (0, renpy_generator_js_1.generateEnding)(cfg);
            const content = (0, renpy_generator_js_1.fileHeader)(`Ending: ${args.title} [${args.ending_type}]`) + "\n" + code;
            fs.mkdirSync(args.output_dir, { recursive: true });
            const filePath = path.join(args.output_dir, `${label}.rpy`);
            fs.writeFileSync(filePath, content, "utf-8");
            return {
                content: [
                    {
                        type: "text",
                        text: [
                            `Ending sequence created: ${args.title}`,
                            `Type: ${args.ending_type}`,
                            `Label: ${label}`,
                            `File: ${filePath}`,
                        ].join("\n"),
                    },
                ],
            };
        },
    },
];
//# sourceMappingURL=eoq-tools.js.map