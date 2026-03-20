import { z } from "zod";
import { ChoiceOption } from "../types.js";
export declare const scriptToolDefs: ({
    name: string;
    description: string;
    inputSchema: z.ZodObject<{
        file_path: z.ZodString;
        label: z.ZodString;
        description: z.ZodString;
        include_defaults: z.ZodDefault<z.ZodOptional<z.ZodBoolean>>;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        label: string;
        description: string;
        include_defaults: boolean;
    }, {
        file_path: string;
        label: string;
        description: string;
        include_defaults?: boolean | undefined;
    }>;
    handler: (args: {
        file_path: string;
        label: string;
        description: string;
        include_defaults: boolean;
    }) => Promise<{
        content: {
            type: string;
            text: string;
        }[];
    }>;
} | {
    name: string;
    description: string;
    inputSchema: z.ZodObject<{
        file_path: z.ZodString;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
    }, {
        file_path: string;
    }>;
    handler: (args: {
        file_path: string;
    }) => Promise<{
        content: {
            type: string;
            text: string;
        }[];
    }>;
} | {
    name: string;
    description: string;
    inputSchema: z.ZodObject<{
        file_path: z.ZodOptional<z.ZodString>;
        content: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        file_path?: string | undefined;
        content?: string | undefined;
    }, {
        file_path?: string | undefined;
        content?: string | undefined;
    }>;
    handler: (args: {
        file_path?: string;
        content?: string;
    }) => Promise<{
        content: {
            type: string;
            text: string;
        }[];
    }>;
} | {
    name: string;
    description: string;
    inputSchema: z.ZodObject<{
        path: z.ZodString;
    }, "strip", z.ZodTypeAny, {
        path: string;
    }, {
        path: string;
    }>;
    handler: (args: {
        path: string;
    }) => Promise<{
        content: {
            type: string;
            text: string;
        }[];
    }>;
} | {
    name: string;
    description: string;
    inputSchema: z.ZodObject<{
        search_dir: z.ZodString;
        symbol: z.ZodString;
    }, "strip", z.ZodTypeAny, {
        symbol: string;
        search_dir: string;
    }, {
        symbol: string;
        search_dir: string;
    }>;
    handler: (args: {
        search_dir: string;
        symbol: string;
    }) => Promise<{
        content: {
            type: string;
            text: string;
        }[];
    }>;
} | {
    name: string;
    description: string;
    inputSchema: z.ZodObject<{
        file_path: z.ZodString;
        speaker: z.ZodString;
        text: z.ZodString;
        tag: z.ZodOptional<z.ZodString>;
        after_label: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        speaker: string;
        text: string;
        tag?: string | undefined;
        after_label?: string | undefined;
    }, {
        file_path: string;
        speaker: string;
        text: string;
        tag?: string | undefined;
        after_label?: string | undefined;
    }>;
    handler: (args: {
        file_path: string;
        speaker: string;
        text: string;
        tag?: string;
        after_label?: string;
    }) => Promise<{
        content: {
            type: string;
            text: string;
        }[];
    }>;
} | {
    name: string;
    description: string;
    inputSchema: z.ZodObject<{
        file_path: z.ZodString;
        label: z.ZodString;
        prompt: z.ZodString;
        options: z.ZodArray<z.ZodObject<{
            text: z.ZodString;
            jump: z.ZodOptional<z.ZodString>;
            condition: z.ZodOptional<z.ZodString>;
            affinity_delta: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodNumber>>;
        }, "strip", z.ZodTypeAny, {
            text: string;
            jump?: string | undefined;
            condition?: string | undefined;
            affinity_delta?: Record<string, number> | undefined;
        }, {
            text: string;
            jump?: string | undefined;
            condition?: string | undefined;
            affinity_delta?: Record<string, number> | undefined;
        }>, "many">;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        label: string;
        options: {
            text: string;
            jump?: string | undefined;
            condition?: string | undefined;
            affinity_delta?: Record<string, number> | undefined;
        }[];
        prompt: string;
    }, {
        file_path: string;
        label: string;
        options: {
            text: string;
            jump?: string | undefined;
            condition?: string | undefined;
            affinity_delta?: Record<string, number> | undefined;
        }[];
        prompt: string;
    }>;
    handler: (args: {
        file_path: string;
        label: string;
        prompt: string;
        options: ChoiceOption[];
    }) => Promise<{
        content: {
            type: string;
            text: string;
        }[];
    }>;
} | {
    name: string;
    description: string;
    inputSchema: z.ZodObject<{
        file_path: z.ZodString;
        text: z.ZodString;
        after_label: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        text: string;
        after_label?: string | undefined;
    }, {
        file_path: string;
        text: string;
        after_label?: string | undefined;
    }>;
    handler: (args: {
        file_path: string;
        text: string;
        after_label?: string;
    }) => Promise<{
        content: {
            type: string;
            text: string;
        }[];
    }>;
} | {
    name: string;
    description: string;
    inputSchema: z.ZodObject<{
        file_a: z.ZodString;
        file_b: z.ZodString;
        output: z.ZodString;
    }, "strip", z.ZodTypeAny, {
        file_a: string;
        file_b: string;
        output: string;
    }, {
        file_a: string;
        file_b: string;
        output: string;
    }>;
    handler: (args: {
        file_a: string;
        file_b: string;
        output: string;
    }) => Promise<{
        content: {
            type: string;
            text: string;
        }[];
    }>;
} | {
    name: string;
    description: string;
    inputSchema: z.ZodObject<{
        path: z.ZodString;
        output_json: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        path: string;
        output_json?: string | undefined;
    }, {
        path: string;
        output_json?: string | undefined;
    }>;
    handler: (args: {
        path: string;
        output_json?: string;
    }) => Promise<{
        content: {
            type: string;
            text: string;
        }[];
    }>;
})[];
//# sourceMappingURL=script-tools.d.ts.map