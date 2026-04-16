import { z } from "zod";
export declare const projectToolDefs: ({
    name: string;
    description: string;
    inputSchema: z.ZodObject<{
        base_dir: z.ZodString;
        name: z.ZodString;
        build_name: z.ZodString;
        version: z.ZodDefault<z.ZodString>;
        developer: z.ZodString;
        copyright: z.ZodString;
    }, "strip", z.ZodTypeAny, {
        name: string;
        base_dir: string;
        build_name: string;
        version: string;
        developer: string;
        copyright: string;
    }, {
        name: string;
        base_dir: string;
        build_name: string;
        developer: string;
        copyright: string;
        version?: string | undefined;
    }>;
    handler: (args: {
        base_dir: string;
        name: string;
        build_name: string;
        version: string;
        developer: string;
        copyright: string;
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
        renpy_executable: z.ZodString;
        project_dir: z.ZodString;
        target: z.ZodDefault<z.ZodEnum<["lint", "compile", "distribute"]>>;
    }, "strip", z.ZodTypeAny, {
        renpy_executable: string;
        project_dir: string;
        target: "lint" | "compile" | "distribute";
    }, {
        renpy_executable: string;
        project_dir: string;
        target?: "lint" | "compile" | "distribute" | undefined;
    }>;
    handler: (args: {
        renpy_executable: string;
        project_dir: string;
        target: string;
    }) => Promise<unknown>;
} | {
    name: string;
    description: string;
    inputSchema: z.ZodObject<{
        game_dir: z.ZodString;
        type: z.ZodDefault<z.ZodOptional<z.ZodEnum<["images", "audio", "fonts", "all"]>>>;
    }, "strip", z.ZodTypeAny, {
        type: "images" | "audio" | "fonts" | "all";
        game_dir: string;
    }, {
        game_dir: string;
        type?: "images" | "audio" | "fonts" | "all" | undefined;
    }>;
    handler: (args: {
        game_dir: string;
        type: string;
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
        scripts_dir: z.ZodString;
        output_dot: z.ZodOptional<z.ZodString>;
        output_json: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        scripts_dir: string;
        output_json?: string | undefined;
        output_dot?: string | undefined;
    }, {
        scripts_dir: string;
        output_json?: string | undefined;
        output_dot?: string | undefined;
    }>;
    handler: (args: {
        scripts_dir: string;
        output_dot?: string;
        output_json?: string;
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
        scripts_dir: z.ZodString;
        output_path: z.ZodString;
        language: z.ZodDefault<z.ZodOptional<z.ZodString>>;
    }, "strip", z.ZodTypeAny, {
        scripts_dir: string;
        output_path: string;
        language: string;
    }, {
        scripts_dir: string;
        output_path: string;
        language?: string | undefined;
    }>;
    handler: (args: {
        scripts_dir: string;
        output_path: string;
        language: string;
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
        accent_color: z.ZodDefault<z.ZodString>;
        foreground_color: z.ZodDefault<z.ZodString>;
        background_color: z.ZodDefault<z.ZodString>;
        hover_color: z.ZodDefault<z.ZodString>;
        font: z.ZodOptional<z.ZodString>;
        name_font: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        accent_color: string;
        foreground_color: string;
        background_color: string;
        hover_color: string;
        font?: string | undefined;
        name_font?: string | undefined;
    }, {
        file_path: string;
        accent_color?: string | undefined;
        foreground_color?: string | undefined;
        background_color?: string | undefined;
        hover_color?: string | undefined;
        font?: string | undefined;
        name_font?: string | undefined;
    }>;
    handler: (args: {
        file_path: string;
        accent_color: string;
        foreground_color: string;
        background_color: string;
        hover_color: string;
        font?: string;
        name_font?: string;
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
        id: z.ZodString;
        name: z.ZodString;
        description: z.ZodString;
        icon: z.ZodOptional<z.ZodString>;
        points: z.ZodOptional<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        description: string;
        id: string;
        name: string;
        icon?: string | undefined;
        points?: number | undefined;
    }, {
        file_path: string;
        description: string;
        id: string;
        name: string;
        icon?: string | undefined;
        points?: number | undefined;
    }>;
    handler: (args: {
        file_path: string;
        id: string;
        name: string;
        description: string;
        icon?: string;
        points?: number;
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
        entries: z.ZodArray<z.ZodObject<{
            id: z.ZodString;
            name: z.ZodString;
            image: z.ZodString;
            unlock_condition: z.ZodString;
            thumbnail: z.ZodOptional<z.ZodString>;
        }, "strip", z.ZodTypeAny, {
            id: string;
            name: string;
            image: string;
            unlock_condition: string;
            thumbnail?: string | undefined;
        }, {
            id: string;
            name: string;
            image: string;
            unlock_condition: string;
            thumbnail?: string | undefined;
        }>, "many">;
    }, "strip", z.ZodTypeAny, {
        entries: {
            id: string;
            name: string;
            image: string;
            unlock_condition: string;
            thumbnail?: string | undefined;
        }[];
        file_path: string;
    }, {
        entries: {
            id: string;
            name: string;
            image: string;
            unlock_condition: string;
            thumbnail?: string | undefined;
        }[];
        file_path: string;
    }>;
    handler: (args: {
        file_path: string;
        entries: {
            id: string;
            name: string;
            image: string;
            unlock_condition: string;
            thumbnail?: string;
        }[];
    }) => Promise<{
        content: {
            type: string;
            text: string;
        }[];
    }>;
})[];
//# sourceMappingURL=project-tools.d.ts.map