// ============================================================
// Scene Building Tools (8 tools)
// ============================================================

import { z } from "zod";
import * as fs from "fs";
import * as path from "path";
import {
  generateScene,
  generateShow,
  generateHide,
  generatePlayMusic,
  generatePlaySound,
  generateTransition,
  generateATLAnimation,
  generateHScene,
  fileHeader,
} from "../renpy-generator.js";
import { HSceneConfig, IntensityLevel } from "../types.js";

export const sceneToolDefs = [
  // 19. renpy_create_scene
  {
    name: "renpy_create_scene",
    description:
      "Create a complete scene block: background, music, character entry, and initial dialogue stub.",
    inputSchema: z.object({
      file_path: z.string().describe("Output .rpy file path"),
      label: z.string().describe("Scene label name"),
      background: z.string().describe("Background image name"),
      music: z.string().optional().describe("Background music file"),
      characters: z
        .array(z.string())
        .optional()
        .default([])
        .describe("Characters to show (image tags)"),
      transition: z
        .string()
        .optional()
        .default("dissolve")
        .describe("Scene entry transition"),
    }),
    handler: async (args: {
      file_path: string;
      label: string;
      background: string;
      music?: string;
      characters: string[];
      transition: string;
    }) => {
      const lines: string[] = [
        `label ${args.label}:`,
        `    ${generateScene(args.background, args.transition)}`,
      ];

      if (args.music) {
        lines.push(`    ${generatePlayMusic(args.music, 1.0, 1.0)}`);
      }

      for (const char of args.characters) {
        lines.push(`    ${generateShow(char, "center", "dissolve")}`);
      }

      lines.push(`    "## Scene ${args.label} — placeholder dialogue"`);
      lines.push(`    return`);
      lines.push(``);

      const content = lines.join("\n");
      let existing = fs.existsSync(args.file_path)
        ? fs.readFileSync(args.file_path, "utf-8")
        : fileHeader(`Scene: ${args.label}`);

      fs.mkdirSync(path.dirname(args.file_path), { recursive: true });
      fs.writeFileSync(args.file_path, existing + "\n" + content, "utf-8");
      return { content: [{ type: "text", text: `Scene created:\n${content}` }] };
    },
  },

  // 20. renpy_add_transition
  {
    name: "renpy_add_transition",
    description: "Add a visual transition statement to a .rpy file after a label.",
    inputSchema: z.object({
      file_path: z.string().describe("Path to .rpy file"),
      transition: z
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
      after_label: z.string().optional().describe("Insert after this label"),
      custom_time: z.number().optional().describe("Custom duration in seconds"),
    }),
    handler: async (args: {
      file_path: string;
      transition: string;
      after_label?: string;
      custom_time?: number;
    }) => {
      let script = fs.readFileSync(args.file_path, "utf-8");
      const transName = args.custom_time
        ? `${args.transition}(${args.custom_time})`
        : args.transition;
      const line = `    ${generateTransition(transName)}`;

      if (args.after_label) {
        const re = new RegExp(`(label\\s+${args.after_label}\\s*:[^\\n]*)`);
        script = script.replace(re, `$1\n${line}`);
      } else {
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
    inputSchema: z.object({
      file_path: z.string().describe("Path to .rpy file"),
      action: z.enum(["show", "hide"]).describe("Whether to show or hide"),
      image: z.string().describe("Image or character tag"),
      at: z.string().optional().describe("Position/transform (e.g. 'left', 'center')"),
      transition: z.string().optional().describe("Transition name"),
      after_label: z.string().optional().describe("Insert after this label"),
    }),
    handler: async (args: {
      file_path: string;
      action: "show" | "hide";
      image: string;
      at?: string;
      transition?: string;
      after_label?: string;
    }) => {
      let script = fs.readFileSync(args.file_path, "utf-8");
      const line =
        args.action === "show"
          ? `    ${generateShow(args.image, args.at, args.transition)}`
          : `    ${generateHide(args.image, args.transition)}`;

      if (args.after_label) {
        const re = new RegExp(`(label\\s+${args.after_label}\\s*:[^\\n]*)`);
        script = script.replace(re, `$1\n${line}`);
      } else {
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
    inputSchema: z.object({
      file_path: z.string().describe("Path to .rpy file"),
      name: z.string().describe("Transform name"),
      frames: z
        .array(
          z.object({
            image: z.string(),
            delay: z.number(),
          })
        )
        .describe("Animation frames with image paths and delays"),
    }),
    handler: async (args: {
      file_path: string;
      name: string;
      frames: { image: string; delay: number }[];
    }) => {
      const code = generateATLAnimation(args.name, args.frames);
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
    inputSchema: z.object({
      file_path: z.string().describe("Path to .rpy file"),
      file: z.string().describe("Audio file path (or 'stop' to stop music)"),
      fadeout: z.number().optional().describe("Fadeout duration in seconds"),
      fadein: z.number().optional().describe("Fadein duration in seconds"),
      channel: z
        .enum(["music", "ambient", "voice"])
        .optional()
        .default("music")
        .describe("Audio channel"),
    }),
    handler: async (args: {
      file_path: string;
      file: string;
      fadeout?: number;
      fadein?: number;
      channel: string;
    }) => {
      let line: string;
      if (args.file === "stop") {
        const fout = args.fadeout ? ` fadeout ${args.fadeout}` : "";
        line = `    stop ${args.channel}${fout}`;
      } else {
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
    inputSchema: z.object({
      file_path: z.string().describe("Path to .rpy file"),
      sound_file: z.string().describe("Sound file path"),
      channel: z
        .string()
        .optional()
        .default("sound")
        .describe("Channel name"),
      after_label: z.string().optional().describe("Insert after this label"),
    }),
    handler: async (args: {
      file_path: string;
      sound_file: string;
      channel: string;
      after_label?: string;
    }) => {
      let script = fs.readFileSync(args.file_path, "utf-8");
      const line = `    ${generatePlaySound(args.sound_file, args.channel)}`;

      if (args.after_label) {
        const re = new RegExp(`(label\\s+${args.after_label}\\s*:[^\\n]*)`);
        script = script.replace(re, `$1\n${line}`);
      } else {
        script = script.trimEnd() + "\n" + line + "\n";
      }

      fs.writeFileSync(args.file_path, script, "utf-8");
      return { content: [{ type: "text", text: `Added SFX:\n${line}` }] };
    },
  },

  // 25. renpy_create_cg_scene
  {
    name: "renpy_create_cg_scene",
    description:
      "Create a CG gallery scene with unlock tracking and viewer label.",
    inputSchema: z.object({
      file_path: z.string().describe("Output .rpy file path"),
      cg_id: z.string().describe("CG identifier (e.g. 'aria_cg01')"),
      cg_image: z.string().describe("Image path for the CG"),
      unlock_condition: z.string().describe("Python condition string to unlock"),
      background_music: z.string().optional().describe("Music during CG"),
      caption: z.string().optional().describe("Caption text shown below CG"),
    }),
    handler: async (args: {
      file_path: string;
      cg_id: string;
      cg_image: string;
      unlock_condition: string;
      background_music?: string;
      caption?: string;
    }) => {
      const lines: string[] = [
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
    description:
      "Create an adult scene scaffold with intensity level and SoulForge DNA parameters.",
    inputSchema: z.object({
      file_path: z.string().describe("Output .rpy file path"),
      label: z.string().describe("Scene label"),
      character_id: z.string().describe("Character variable name"),
      dna: z.object({
        name: z.string(),
        archetype: z.string(),
        affinity_type: z.string(),
        corruption_vector: z.string(),
        kink_profile: z.array(z.string()),
        voice_style: z.string(),
        color_hex: z.string(),
        sprite_style: z.string(),
      }),
      intensity: z
        .enum(["soft", "medium", "explicit", "extreme"])
        .describe("Scene intensity level"),
      corruption_stage: z.number().min(1).max(5).describe("Corruption stage (1-5)"),
      acts: z
        .array(
          z.object({
            id: z.string(),
            description: z.string(),
            dialogue_count: z.number(),
            has_cg: z.boolean(),
          })
        )
        .describe("Scene acts"),
      unlock_condition: z.string().optional().describe("Python condition to unlock"),
      cg_prefix: z.string().optional().describe("CG image name prefix"),
    }),
    handler: async (args: {
      file_path: string;
      label: string;
      character_id: string;
      dna: HSceneConfig["dna"];
      intensity: IntensityLevel;
      corruption_stage: number;
      acts: HSceneConfig["acts"];
      unlock_condition?: string;
      cg_prefix?: string;
    }) => {
      const cfg: HSceneConfig = {
        label: args.label,
        character_id: args.character_id,
        dna: args.dna,
        intensity: args.intensity,
        corruption_stage: args.corruption_stage,
        acts: args.acts,
        unlock_condition: args.unlock_condition,
        cg_prefix: args.cg_prefix,
      };

      const code = generateHScene(cfg);
      let existing = fs.existsSync(args.file_path)
        ? fs.readFileSync(args.file_path, "utf-8")
        : "";
      fs.mkdirSync(path.dirname(args.file_path), { recursive: true });
      fs.writeFileSync(args.file_path, existing + "\n" + code + "\n", "utf-8");
      return { content: [{ type: "text", text: `H-scene scaffold created:\n${code}` }] };
    },
  },
];
