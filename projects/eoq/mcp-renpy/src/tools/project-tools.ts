// ============================================================
// Project Management Tools (8 tools)
// ============================================================

import { z } from "zod";
import * as fs from "fs";
import * as path from "path";
import * as child_process from "child_process";
import {
  generateProjectOptions,
  renderFlowchartDot,
  parseFlowchart,
  generateGalleryEntry,
  generateAchievement,
} from "../renpy-generator.js";

export const projectToolDefs = [
  // 35. renpy_init_project
  {
    name: "renpy_init_project",
    description:
      "Initialize a new Ren'Py project directory structure with standard files.",
    inputSchema: z.object({
      base_dir: z.string().describe("Root directory for the project"),
      name: z.string().describe("Game name"),
      build_name: z
        .string()
        .describe("Build name (no spaces, used for file names)"),
      version: z.string().default("1.0.0").describe("Game version"),
      developer: z.string().describe("Developer name"),
      copyright: z.string().describe("Copyright string"),
    }),
    handler: async (args: {
      base_dir: string;
      name: string;
      build_name: string;
      version: string;
      developer: string;
      copyright: string;
    }) => {
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
      const options = generateProjectOptions({
        name: args.name,
        build_name: args.build_name,
        version: args.version,
        developer: args.developer,
        copyright: args.copyright,
      });
      fs.writeFileSync(
        path.join(args.base_dir, "game/options.rpy"),
        `## Game options\n\n${options}\n`,
        "utf-8"
      );

      // script.rpy
      fs.writeFileSync(
        path.join(args.base_dir, "game/script.rpy"),
        [
          `## Main script entry point`,
          ``,
          `label start:`,
          `    "## Game start — replace with opening scene"`,
          `    jump main_menu`,
          ``,
          `label main_menu:`,
          `    return`,
        ].join("\n"),
        "utf-8"
      );

      // characters.rpy
      fs.writeFileSync(
        path.join(args.base_dir, "game/scripts/characters.rpy"),
        `## Character definitions\n\n`,
        "utf-8"
      );

      // variables.rpy
      fs.writeFileSync(
        path.join(args.base_dir, "game/scripts/variables.rpy"),
        `## Game variables and defaults\n\n`,
        "utf-8"
      );

      // screens.rpy stub
      fs.writeFileSync(
        path.join(args.base_dir, "game/scripts/screens.rpy"),
        `## Custom screens\n\n`,
        "utf-8"
      );

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
    description:
      "Build/compile a Ren'Py project using the Ren'Py launcher CLI.",
    inputSchema: z.object({
      renpy_executable: z
        .string()
        .describe("Path to renpy.sh or renpy.exe"),
      project_dir: z.string().describe("Path to the project root"),
      target: z
        .enum(["lint", "compile", "distribute"])
        .default("compile")
        .describe("Build target"),
    }),
    handler: async (args: {
      renpy_executable: string;
      project_dir: string;
      target: string;
    }) => {
      const targetFlag =
        args.target === "lint"
          ? "lint"
          : args.target === "distribute"
          ? "distribute"
          : "compile";

      return new Promise((resolve) => {
        child_process.exec(
          `"${args.renpy_executable}" "${args.project_dir}" ${targetFlag}`,
          { timeout: 120000 },
          (error, stdout, stderr) => {
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
          }
        );
      });
    },
  },

  // 37. renpy_list_assets
  {
    name: "renpy_list_assets",
    description:
      "List all game assets (images, audio, fonts) in a project directory.",
    inputSchema: z.object({
      game_dir: z.string().describe("Path to the game/ directory"),
      type: z
        .enum(["images", "audio", "fonts", "all"])
        .optional()
        .default("all")
        .describe("Asset type filter"),
    }),
    handler: async (args: { game_dir: string; type: string }) => {
      const extensions: Record<string, string[]> = {
        images: [".png", ".jpg", ".jpeg", ".webp", ".gif"],
        audio: [".ogg", ".mp3", ".wav", ".opus"],
        fonts: [".ttf", ".otf"],
      };

      const exts =
        args.type === "all"
          ? Object.values(extensions).flat()
          : extensions[args.type] ?? [];

      const walkDir = (dir: string): string[] => {
        if (!fs.existsSync(dir)) return [];
        const results: string[] = [];
        const entries = fs.readdirSync(dir, { withFileTypes: true });
        for (const entry of entries) {
          const full = path.join(dir, entry.name);
          if (entry.isDirectory()) {
            results.push(...walkDir(full));
          } else if (exts.some((e) => entry.name.endsWith(e))) {
            results.push(full);
          }
        }
        return results;
      };

      const assets = walkDir(args.game_dir);
      const byType: Record<string, string[]> = {};
      for (const asset of assets) {
        const ext = path.extname(asset).toLowerCase();
        const category =
          Object.entries(extensions).find(([, exts]) => exts.includes(ext))?.[0] ??
          "other";
        if (!byType[category]) byType[category] = [];
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
    description:
      "Generate a Graphviz DOT flowchart from all .rpy scripts in a directory.",
    inputSchema: z.object({
      scripts_dir: z.string().describe("Directory containing .rpy files"),
      output_dot: z
        .string()
        .optional()
        .describe("Output path for .dot file"),
      output_json: z
        .string()
        .optional()
        .describe("Output path for JSON node data"),
    }),
    handler: async (args: {
      scripts_dir: string;
      output_dot?: string;
      output_json?: string;
    }) => {
      const entries = fs.readdirSync(args.scripts_dir, { recursive: true }) as string[];
      const rpyFiles = entries
        .filter((e) => e.endsWith(".rpy"))
        .map((e) => path.join(args.scripts_dir, e));

      const allScript = rpyFiles
        .map((f) => fs.readFileSync(f, "utf-8"))
        .join("\n\n");

      const nodes = parseFlowchart(allScript);
      const dot = renderFlowchartDot(nodes);

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
    description:
      "Export all dialogue strings to a JSON translation template file.",
    inputSchema: z.object({
      scripts_dir: z.string().describe("Directory containing .rpy files"),
      output_path: z.string().describe("Output .json path for translation"),
      language: z
        .string()
        .optional()
        .default("english")
        .describe("Target language identifier"),
    }),
    handler: async (args: {
      scripts_dir: string;
      output_path: string;
      language: string;
    }) => {
      const entries = fs.readdirSync(args.scripts_dir, { recursive: true }) as string[];
      const rpyFiles = entries
        .filter((e) => e.endsWith(".rpy"))
        .map((e) => path.join(args.scripts_dir, e));

      const translations: Record<string, string> = {};
      const dialogueRe = /^\s+\w+\s+"([^"]+)"/gm;
      const narratorRe = /^\s+"([^"]+)"/gm;

      for (const file of rpyFiles) {
        const script = fs.readFileSync(file, "utf-8");
        let m: RegExpExecArray | null;

        const dr = new RegExp(dialogueRe.source, dialogueRe.flags);
        while ((m = dr.exec(script)) !== null) {
          if (!m[1].startsWith("##")) translations[m[1]] = m[1];
        }

        const nr = new RegExp(narratorRe.source, narratorRe.flags);
        while ((m = nr.exec(script)) !== null) {
          if (!m[1].startsWith("##")) translations[m[1]] = m[1];
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
    description:
      "Generate a GUI customization block (colors, fonts, layout) for gui.rpy.",
    inputSchema: z.object({
      file_path: z.string().describe("Path to gui.rpy"),
      accent_color: z
        .string()
        .default("#c8a0ff")
        .describe("Primary accent color"),
      foreground_color: z.string().default("#ffffff").describe("Text color"),
      background_color: z.string().default("#1a0a2e").describe("Background color"),
      hover_color: z
        .string()
        .default("#ff80b4")
        .describe("Hover/highlight color"),
      font: z
        .string()
        .optional()
        .describe("Path to custom font file"),
      name_font: z
        .string()
        .optional()
        .describe("Path to character name font"),
    }),
    handler: async (args: {
      file_path: string;
      accent_color: string;
      foreground_color: string;
      background_color: string;
      hover_color: string;
      font?: string;
      name_font?: string;
    }) => {
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
    inputSchema: z.object({
      file_path: z.string().describe("Path to achievements .rpy file"),
      id: z.string().describe("Achievement ID (snake_case)"),
      name: z.string().describe("Display name"),
      description: z.string().describe("Achievement description"),
      icon: z.string().optional().describe("Icon image path"),
      points: z.number().optional().describe("Points value"),
    }),
    handler: async (args: {
      file_path: string;
      id: string;
      name: string;
      description: string;
      icon?: string;
      points?: number;
    }) => {
      const code = generateAchievement(
        args.id,
        args.name,
        args.description,
        args.icon,
        args.points
      );
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
    description:
      "Generate a gallery screen and unlock tracking for a list of CG entries.",
    inputSchema: z.object({
      file_path: z.string().describe("Output .rpy file for gallery"),
      entries: z
        .array(
          z.object({
            id: z.string(),
            name: z.string(),
            image: z.string(),
            unlock_condition: z.string(),
            thumbnail: z.string().optional(),
          })
        )
        .describe("Gallery CG entries"),
    }),
    handler: async (args: {
      file_path: string;
      entries: {
        id: string;
        name: string;
        image: string;
        unlock_condition: string;
        thumbnail?: string;
      }[];
    }) => {
      const lines: string[] = [
        `## CG Gallery — EoBQ`,
        `## Generated by mcp-renpy`,
        ``,
        `init python:`,
        `    gallery = Gallery()`,
        ``,
      ];

      for (const entry of args.entries) {
        lines.push(
          generateGalleryEntry(
            entry.id,
            entry.name,
            entry.image,
            entry.unlock_condition,
            entry.thumbnail
          )
        );
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
