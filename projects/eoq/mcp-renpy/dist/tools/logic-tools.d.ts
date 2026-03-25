import { z } from "zod";
import { EndingType, AffinityConfig } from "../types.js";
export declare const logicToolDefs: ({
    name: string;
    description: string;
    inputSchema: z.ZodObject<{
        file_path: z.ZodString;
        name: z.ZodString;
        value: z.ZodString;
        is_define: z.ZodDefault<z.ZodOptional<z.ZodBoolean>>;
        description: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        value: string;
        name: string;
        is_define: boolean;
        description?: string | undefined;
    }, {
        file_path: string;
        value: string;
        name: string;
        description?: string | undefined;
        is_define?: boolean | undefined;
    }>;
    handler: (args: {
        file_path: string;
        name: string;
        value: string;
        is_define: boolean;
        description?: string;
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
        conditions: z.ZodArray<z.ZodObject<{
            condition: z.ZodString;
            body: z.ZodArray<z.ZodString, "many">;
        }, "strip", z.ZodTypeAny, {
            condition: string;
            body: string[];
        }, {
            condition: string;
            body: string[];
        }>, "many">;
        else_body: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
        indent_level: z.ZodDefault<z.ZodOptional<z.ZodNumber>>;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        conditions: {
            condition: string;
            body: string[];
        }[];
        indent_level: number;
        else_body?: string[] | undefined;
    }, {
        file_path: string;
        conditions: {
            condition: string;
            body: string[];
        }[];
        else_body?: string[] | undefined;
        indent_level?: number | undefined;
    }>;
    handler: (args: {
        file_path: string;
        conditions: {
            condition: string;
            body: string[];
        }[];
        else_body?: string[];
        indent_level: number;
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
        code: z.ZodString;
        is_init: z.ZodDefault<z.ZodOptional<z.ZodBoolean>>;
        init_priority: z.ZodOptional<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        code: string;
        is_init: boolean;
        init_priority?: number | undefined;
    }, {
        file_path: string;
        code: string;
        is_init?: boolean | undefined;
        init_priority?: number | undefined;
    }>;
    handler: (args: {
        file_path: string;
        code: string;
        is_init: boolean;
        init_priority?: number;
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
        name: z.ZodString;
        params: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
        body: z.ZodString;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        name: string;
        body: string;
        params?: string[] | undefined;
    }, {
        file_path: string;
        name: string;
        body: string;
        params?: string[] | undefined;
    }>;
    handler: (args: {
        file_path: string;
        name: string;
        params?: string[];
        body: string;
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
        name: z.ZodString;
        body: z.ZodString;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        name: string;
        body: string;
    }, {
        file_path: string;
        name: string;
        body: string;
    }>;
    handler: (args: {
        file_path: string;
        name: string;
        body: string;
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
        character_id: z.ZodString;
        variable_name: z.ZodString;
        thresholds: z.ZodObject<{
            low: z.ZodDefault<z.ZodNumber>;
            medium: z.ZodDefault<z.ZodNumber>;
            high: z.ZodDefault<z.ZodNumber>;
            max: z.ZodDefault<z.ZodNumber>;
        }, "strip", z.ZodTypeAny, {
            medium: number;
            low: number;
            high: number;
            max: number;
        }, {
            medium?: number | undefined;
            low?: number | undefined;
            high?: number | undefined;
            max?: number | undefined;
        }>;
        route_unlock_threshold: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        character_id: string;
        variable_name: string;
        thresholds: {
            medium: number;
            low: number;
            high: number;
            max: number;
        };
        route_unlock_threshold: number;
    }, {
        file_path: string;
        character_id: string;
        variable_name: string;
        thresholds: {
            medium?: number | undefined;
            low?: number | undefined;
            high?: number | undefined;
            max?: number | undefined;
        };
        route_unlock_threshold: number;
    }>;
    handler: (args: {
        file_path: string;
        character_id: string;
        variable_name: string;
        thresholds: AffinityConfig["thresholds"];
        route_unlock_threshold: number;
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
        flag_name: z.ZodString;
        description: z.ZodString;
        default_value: z.ZodDefault<z.ZodOptional<z.ZodBoolean>>;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        description: string;
        flag_name: string;
        default_value: boolean;
    }, {
        file_path: string;
        description: string;
        flag_name: string;
        default_value?: boolean | undefined;
    }>;
    handler: (args: {
        file_path: string;
        flag_name: string;
        description: string;
        default_value: boolean;
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
        type: z.ZodEnum<["true_love", "corruption_complete", "harem_empress", "burned_out", "queen_ascendant", "mutual_destruction", "secret_escape", "bad_end"]>;
        label: z.ZodString;
        conditions: z.ZodArray<z.ZodString, "many">;
        title: z.ZodString;
        music: z.ZodOptional<z.ZodString>;
        cg: z.ZodOptional<z.ZodString>;
        description: z.ZodString;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        label: string;
        description: string;
        type: "true_love" | "corruption_complete" | "harem_empress" | "burned_out" | "queen_ascendant" | "mutual_destruction" | "secret_escape" | "bad_end";
        conditions: string[];
        title: string;
        cg?: string | undefined;
        music?: string | undefined;
    }, {
        file_path: string;
        label: string;
        description: string;
        type: "true_love" | "corruption_complete" | "harem_empress" | "burned_out" | "queen_ascendant" | "mutual_destruction" | "secret_escape" | "bad_end";
        conditions: string[];
        title: string;
        cg?: string | undefined;
        music?: string | undefined;
    }>;
    handler: (args: {
        file_path: string;
        type: EndingType;
        label: string;
        conditions: string[];
        title: string;
        music?: string;
        cg?: string;
        description: string;
    }) => Promise<{
        content: {
            type: string;
            text: string;
        }[];
    }>;
})[];
//# sourceMappingURL=logic-tools.d.ts.map