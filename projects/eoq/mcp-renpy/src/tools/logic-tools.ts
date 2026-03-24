// ============================================================
// Variable & Logic Tools (8 tools)
// ============================================================

import { z } from "zod";
import * as fs from "fs";
import * as path from "path";
import {
  generateDefault,
  generateDefine,
  generateConditionBlock,
  generatePythonBlock,
  generateScreen,
  generateATLTransform,
  generateAffinityDefaults,
  generateEnding,
} from "../renpy-generator.js";
import { EndingConfig, EndingType, AffinityConfig } from "../types.js";

export const logicToolDefs = [
  // 27. renpy_define_variable
  {
    name: "renpy_define_variable",
    description:
      "Define a game variable with a default value, with optional type annotation comment.",
    inputSchema: z.object({
      file_path: z.string().describe("Path to variables .rpy file"),
      name: z.string().describe("Variable name"),
      value: z.string().describe("Default value (Python literal)"),
      is_define: z
        .boolean()
        .optional()
        .default(false)
        .describe("Use 'define' instead of 'default' (for constants)"),
      description: z
        .string()
        .optional()
        .describe("Optional comment describing the variable"),
    }),
    handler: async (args: {
      file_path: string;
      name: string;
      value: string;
      is_define: boolean;
      description?: string;
    }) => {
      const comment = args.description ? `## ${args.description}\n` : "";
      const line = args.is_define
        ? generateDefine(args.name, args.value)
        : generateDefault(args.name, args.value);

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
    inputSchema: z.object({
      file_path: z.string().describe("Path to .rpy file"),
      conditions: z
        .array(
          z.object({
            condition: z.string().describe("Python condition expression"),
            body: z.array(z.string()).describe("Lines to execute"),
          })
        )
        .describe("if/elif branches"),
      else_body: z
        .array(z.string())
        .optional()
        .describe("else branch lines"),
      indent_level: z
        .number()
        .optional()
        .default(1)
        .describe("Base indentation level (1 = 4 spaces)"),
    }),
    handler: async (args: {
      file_path: string;
      conditions: { condition: string; body: string[] }[];
      else_body?: string[];
      indent_level: number;
    }) => {
      const pad = "    ".repeat(args.indent_level);
      const block = generateConditionBlock(args.conditions, args.else_body);
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
    inputSchema: z.object({
      file_path: z.string().describe("Path to .rpy file"),
      code: z.string().describe("Python code to insert"),
      is_init: z
        .boolean()
        .optional()
        .default(false)
        .describe("Use 'init python:' block instead of 'python:'"),
      init_priority: z
        .number()
        .optional()
        .describe("Init block priority (if is_init)"),
    }),
    handler: async (args: {
      file_path: string;
      code: string;
      is_init: boolean;
      init_priority?: number;
    }) => {
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
    inputSchema: z.object({
      file_path: z.string().describe("Path to screens .rpy file"),
      name: z.string().describe("Screen name"),
      params: z
        .array(z.string())
        .optional()
        .describe("Screen parameters"),
      body: z.string().describe("Screen body (indented Ren'Py screen language)"),
    }),
    handler: async (args: {
      file_path: string;
      name: string;
      params?: string[];
      body: string;
    }) => {
      const code = generateScreen({ name: args.name, params: args.params, body: args.body });
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
    inputSchema: z.object({
      file_path: z.string().describe("Path to transforms .rpy file"),
      name: z.string().describe("Transform name"),
      body: z
        .string()
        .describe("ATL body (e.g. 'xalign 0.5\\nyalign 1.0\\npause 0.5\\nrepeat')"),
    }),
    handler: async (args: { file_path: string; name: string; body: string }) => {
      const code = generateATLTransform({ name: args.name, body: args.body });
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
    description:
      "Generate affinity tracking defaults and helper label for a character.",
    inputSchema: z.object({
      file_path: z.string().describe("Output .rpy file path"),
      character_id: z.string().describe("Character ID"),
      variable_name: z.string().describe("Affinity variable name (e.g. 'aria_affinity')"),
      thresholds: z.object({
        low: z.number().default(10),
        medium: z.number().default(30),
        high: z.number().default(60),
        max: z.number().default(100),
      }),
      route_unlock_threshold: z.number().describe("Threshold to unlock route"),
    }),
    handler: async (args: {
      file_path: string;
      character_id: string;
      variable_name: string;
      thresholds: AffinityConfig["thresholds"];
      route_unlock_threshold: number;
    }) => {
      const cfg: AffinityConfig = {
        character_id: args.character_id,
        variable_name: args.variable_name,
        thresholds: args.thresholds,
        route_unlock_threshold: args.route_unlock_threshold,
      };
      const code = generateAffinityDefaults(cfg);
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
    description:
      "Add a story flag variable (boolean default False) with a description comment.",
    inputSchema: z.object({
      file_path: z.string().describe("Path to flags .rpy file"),
      flag_name: z.string().describe("Flag variable name (e.g. 'aria_told_truth')"),
      description: z.string().describe("Human-readable flag description"),
      default_value: z
        .boolean()
        .optional()
        .default(false)
        .describe("Initial value"),
    }),
    handler: async (args: {
      file_path: string;
      flag_name: string;
      description: string;
      default_value: boolean;
    }) => {
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
    description:
      "Create one of the 8 EoBQ ending types with conditions, music, and CG stubs.",
    inputSchema: z.object({
      file_path: z.string().describe("Output .rpy file path"),
      type: z
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
      label: z.string().describe("Ending label name"),
      conditions: z.array(z.string()).describe("Conditions required to reach this ending"),
      title: z.string().describe("Ending title shown to player"),
      music: z.string().optional().describe("Ending music file"),
      cg: z.string().optional().describe("Ending CG image name"),
      description: z.string().describe("Narrative description of the ending"),
    }),
    handler: async (args: {
      file_path: string;
      type: EndingType;
      label: string;
      conditions: string[];
      title: string;
      music?: string;
      cg?: string;
      description: string;
    }) => {
      const cfg: EndingConfig = {
        type: args.type,
        label: args.label,
        conditions: args.conditions,
        title: args.title,
        music: args.music,
        cg: args.cg,
        description: args.description,
      };
      const code = generateEnding(cfg);
      let existing = fs.existsSync(args.file_path)
        ? fs.readFileSync(args.file_path, "utf-8")
        : "";
      fs.mkdirSync(path.dirname(args.file_path), { recursive: true });
      fs.writeFileSync(args.file_path, existing + "\n" + code + "\n", "utf-8");
      return { content: [{ type: "text", text: `Ending created:\n${code}` }] };
    },
  },
];
