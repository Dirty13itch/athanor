// ============================================================
// Script Management Tools (10 tools)
// ============================================================

import { z } from "zod";
import * as fs from "fs";
import * as path from "path";
import {
  fileHeader,
  generateLabel,
  generateDialogue,
  generateNarration,
  generateChoiceMenu,
  mergeScripts,
  extractTranslatableStrings,
  validateScript,
  parseFlowchart,
} from "../renpy-generator.js";
import { ChoiceOption } from "../types.js";

export const scriptToolDefs = [
  // 1. renpy_create_script
  {
    name: "renpy_create_script",
    description:
      "Create a new .rpy script file with boilerplate. Returns the path of the created file.",
    inputSchema: z.object({
      file_path: z.string().describe("Absolute path for the new .rpy file"),
      label: z.string().describe("Initial label name to create"),
      description: z.string().describe("Human-readable file description"),
      include_defaults: z
        .boolean()
        .optional()
        .default(true)
        .describe("Include default boilerplate (init block, etc.)"),
    }),
    handler: async (args: {
      file_path: string;
      label: string;
      description: string;
      include_defaults: boolean;
    }) => {
      const header = fileHeader(args.description);
      const body: string[] = [
        `"## Scene placeholder"`,
        `return`,
      ];
      const labelBlock = generateLabel(args.label, body);

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
    description:
      "Parse an existing .rpy file and return a structured summary of labels, characters, and jumps.",
    inputSchema: z.object({
      file_path: z.string().describe("Path to the .rpy file to parse"),
    }),
    handler: async (args: { file_path: string }) => {
      const script = fs.readFileSync(args.file_path, "utf-8");
      const nodes = parseFlowchart(script);

      const labels = nodes.map((n) => n.label);
      const allJumps = nodes.flatMap((n) => n.jumps);
      const allCalls = nodes.flatMap((n) => n.calls);

      // Extract character definitions
      const charRegex = /define\s+(\w+)\s*=\s*Character\(/g;
      const chars: string[] = [];
      let m: RegExpExecArray | null;
      while ((m = charRegex.exec(script)) !== null) chars.push(m[1]);

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
    description:
      "Validate a .rpy file for syntax errors (unclosed quotes, duplicate labels, unresolved jumps).",
    inputSchema: z.object({
      file_path: z
        .string()
        .optional()
        .describe("Path to .rpy file (mutually exclusive with content)"),
      content: z
        .string()
        .optional()
        .describe("Raw script content to validate"),
    }),
    handler: async (args: { file_path?: string; content?: string }) => {
      let script = args.content ?? "";
      if (args.file_path && !args.content) {
        script = fs.readFileSync(args.file_path, "utf-8");
      }
      const result = validateScript(script);
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
    inputSchema: z.object({
      path: z.string().describe("Path to .rpy file or directory"),
    }),
    handler: async (args: { path: string }) => {
      const stat = fs.statSync(args.path);
      const files: string[] = [];
      if (stat.isDirectory()) {
        const entries = fs.readdirSync(args.path, { recursive: true }) as string[];
        files.push(
          ...entries
            .filter((e) => e.endsWith(".rpy"))
            .map((e) => path.join(args.path, e))
        );
      } else {
        files.push(args.path);
      }

      const result: Record<string, string[]> = {};
      for (const f of files) {
        const script = fs.readFileSync(f, "utf-8");
        const labels: string[] = [];
        const re = /^label\s+(\w+)\s*:/gm;
        let m: RegExpExecArray | null;
        while ((m = re.exec(script)) !== null) labels.push(m[1]);
        result[f] = labels;
      }

      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    },
  },

  // 5. renpy_find_references
  {
    name: "renpy_find_references",
    description:
      "Find all references (jumps, calls, show commands) to a given label or variable name across .rpy files.",
    inputSchema: z.object({
      search_dir: z.string().describe("Directory to search"),
      symbol: z.string().describe("Label or variable name to find"),
    }),
    handler: async (args: { search_dir: string; symbol: string }) => {
      const entries = fs.readdirSync(args.search_dir, { recursive: true }) as string[];
      const rpyFiles = entries
        .filter((e) => e.endsWith(".rpy"))
        .map((e) => path.join(args.search_dir, e));

      const refs: { file: string; line: number; text: string }[] = [];
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
    inputSchema: z.object({
      file_path: z.string().describe("Path to the .rpy file"),
      speaker: z.string().describe("Character variable name (e.g. 'aria')"),
      text: z.string().describe("Dialogue text"),
      tag: z.string().optional().describe("Expression tag (e.g. 'smile')"),
      after_label: z
        .string()
        .optional()
        .describe("Insert after this label instead of appending"),
    }),
    handler: async (args: {
      file_path: string;
      speaker: string;
      text: string;
      tag?: string;
      after_label?: string;
    }) => {
      let script = fs.readFileSync(args.file_path, "utf-8");
      const line = `    ${generateDialogue(args.speaker, args.text, args.tag)}`;

      if (args.after_label) {
        const re = new RegExp(`(label\\s+${args.after_label}\\s*:[^\\n]*)`, "");
        script = script.replace(re, `$1\n${line}`);
      } else {
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
    inputSchema: z.object({
      file_path: z.string().describe("Path to the .rpy file to append to"),
      label: z.string().describe("Label to insert the menu under"),
      prompt: z.string().describe("Menu prompt text (shown above choices)"),
      options: z
        .array(
          z.object({
            text: z.string(),
            jump: z.string().optional(),
            condition: z.string().optional(),
            affinity_delta: z.record(z.number()).optional(),
          })
        )
        .describe("Array of choice options"),
    }),
    handler: async (args: {
      file_path: string;
      label: string;
      prompt: string;
      options: ChoiceOption[];
    }) => {
      let script = fs.readFileSync(args.file_path, "utf-8");
      const menuBlock = generateChoiceMenu(args.prompt, args.options);
      const indented = menuBlock
        .split("\n")
        .map((l) => `    ${l}`)
        .join("\n");

      const re = new RegExp(`(label\\s+${args.label}\\s*:)`, "");
      if (re.test(script)) {
        script = script.replace(re, `$1\n${indented}`);
      } else {
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
    inputSchema: z.object({
      file_path: z.string().describe("Path to the .rpy file"),
      text: z.string().describe("Narration text"),
      after_label: z.string().optional().describe("Insert after this label"),
    }),
    handler: async (args: { file_path: string; text: string; after_label?: string }) => {
      let script = fs.readFileSync(args.file_path, "utf-8");
      const line = `    ${generateNarration(args.text)}`;

      if (args.after_label) {
        const re = new RegExp(`(label\\s+${args.after_label}\\s*:)`);
        script = script.replace(re, `$1\n${line}`);
      } else {
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
    inputSchema: z.object({
      file_a: z.string().describe("First .rpy file path"),
      file_b: z.string().describe("Second .rpy file path"),
      output: z.string().describe("Output file path"),
    }),
    handler: async (args: { file_a: string; file_b: string; output: string }) => {
      const a = fs.readFileSync(args.file_a, "utf-8");
      const b = fs.readFileSync(args.file_b, "utf-8");
      const merged = mergeScripts(a, b);
      const validation = validateScript(merged);
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
    description:
      "Extract all translatable strings from a .rpy file or directory for localization.",
    inputSchema: z.object({
      path: z.string().describe("Path to .rpy file or directory"),
      output_json: z
        .string()
        .optional()
        .describe("If provided, write JSON output to this path"),
    }),
    handler: async (args: { path: string; output_json?: string }) => {
      const stat = fs.statSync(args.path);
      const files: string[] = [];
      if (stat.isDirectory()) {
        const entries = fs.readdirSync(args.path, { recursive: true }) as string[];
        files.push(
          ...entries
            .filter((e) => e.endsWith(".rpy"))
            .map((e) => path.join(args.path, e))
        );
      } else {
        files.push(args.path);
      }

      const allStrings: Record<string, string[]> = {};
      for (const f of files) {
        const script = fs.readFileSync(f, "utf-8");
        allStrings[f] = extractTranslatableStrings(script);
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
