import { z } from "zod";
import { CharacterDNA, RenpyCharacterDef, LayeredImageConfig } from "../types.js";
export declare const characterToolDefs: ({
    name: string;
    description: string;
    inputSchema: z.ZodObject<{
        file_path: z.ZodString;
        id: z.ZodString;
        name: z.ZodString;
        color: z.ZodString;
        voice_tag: z.ZodOptional<z.ZodString>;
        what_font: z.ZodOptional<z.ZodString>;
        what_size: z.ZodOptional<z.ZodNumber>;
        image: z.ZodOptional<z.ZodString>;
        callback: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        id: string;
        name: string;
        color: string;
        voice_tag?: string | undefined;
        what_font?: string | undefined;
        what_size?: number | undefined;
        image?: string | undefined;
        callback?: string | undefined;
    }, {
        file_path: string;
        id: string;
        name: string;
        color: string;
        voice_tag?: string | undefined;
        what_font?: string | undefined;
        what_size?: number | undefined;
        image?: string | undefined;
        callback?: string | undefined;
    }>;
    handler: (args: RenpyCharacterDef & {
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
        search_dir: z.ZodString;
    }, "strip", z.ZodTypeAny, {
        search_dir: string;
    }, {
        search_dir: string;
    }>;
    handler: (args: {
        search_dir: string;
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
        updates: z.ZodRecord<z.ZodString, z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        id: string;
        updates: Record<string, string>;
    }, {
        file_path: string;
        id: string;
        updates: Record<string, string>;
    }>;
    handler: (args: {
        file_path: string;
        id: string;
        updates: Record<string, string>;
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
        expression: z.ZodString;
        image_path: z.ZodString;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        character_id: string;
        expression: string;
        image_path: string;
    }, {
        file_path: string;
        character_id: string;
        expression: string;
        image_path: string;
    }>;
    handler: (args: {
        file_path: string;
        character_id: string;
        expression: string;
        image_path: string;
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
        dna: z.ZodObject<{
            name: z.ZodString;
            archetype: z.ZodString;
            affinity_type: z.ZodString;
            corruption_vector: z.ZodString;
            kink_profile: z.ZodArray<z.ZodString, "many">;
            voice_style: z.ZodString;
            color_hex: z.ZodString;
            sprite_style: z.ZodString;
        }, "strip", z.ZodTypeAny, {
            name: string;
            archetype: string;
            affinity_type: string;
            corruption_vector: string;
            kink_profile: string[];
            voice_style: string;
            color_hex: string;
            sprite_style: string;
        }, {
            name: string;
            archetype: string;
            affinity_type: string;
            corruption_vector: string;
            kink_profile: string[];
            voice_style: string;
            color_hex: string;
            sprite_style: string;
        }>;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        dna: {
            name: string;
            archetype: string;
            affinity_type: string;
            corruption_vector: string;
            kink_profile: string[];
            voice_style: string;
            color_hex: string;
            sprite_style: string;
        };
    }, {
        file_path: string;
        dna: {
            name: string;
            archetype: string;
            affinity_type: string;
            corruption_vector: string;
            kink_profile: string[];
            voice_style: string;
            color_hex: string;
            sprite_style: string;
        };
    }>;
    handler: (args: {
        file_path: string;
        dna: CharacterDNA;
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
        base: z.ZodOptional<z.ZodString>;
        attributes: z.ZodArray<z.ZodObject<{
            group: z.ZodString;
            values: z.ZodArray<z.ZodString, "many">;
            default: z.ZodOptional<z.ZodString>;
        }, "strip", z.ZodTypeAny, {
            values: string[];
            group: string;
            default?: string | undefined;
        }, {
            values: string[];
            group: string;
            default?: string | undefined;
        }>, "many">;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        name: string;
        attributes: {
            values: string[];
            group: string;
            default?: string | undefined;
        }[];
        base?: string | undefined;
    }, {
        file_path: string;
        name: string;
        attributes: {
            values: string[];
            group: string;
            default?: string | undefined;
        }[];
        base?: string | undefined;
    }>;
    handler: (args: {
        file_path: string;
        name: string;
        base?: string;
        attributes: LayeredImageConfig["attributes"];
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
        voice_tag: z.ZodString;
        voice_file_pattern: z.ZodString;
        sustain: z.ZodDefault<z.ZodOptional<z.ZodBoolean>>;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        voice_tag: string;
        character_id: string;
        voice_file_pattern: string;
        sustain: boolean;
    }, {
        file_path: string;
        voice_tag: string;
        character_id: string;
        voice_file_pattern: string;
        sustain?: boolean | undefined;
    }>;
    handler: (args: {
        file_path: string;
        character_id: string;
        voice_tag: string;
        voice_file_pattern: string;
        sustain: boolean;
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
        character_name: z.ZodString;
        acts: z.ZodNumber;
        scenes_per_act: z.ZodNumber;
        include_affinity: z.ZodDefault<z.ZodOptional<z.ZodBoolean>>;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        character_id: string;
        character_name: string;
        acts: number;
        scenes_per_act: number;
        include_affinity: boolean;
    }, {
        file_path: string;
        character_id: string;
        character_name: string;
        acts: number;
        scenes_per_act: number;
        include_affinity?: boolean | undefined;
    }>;
    handler: (args: {
        file_path: string;
        character_id: string;
        character_name: string;
        acts: number;
        scenes_per_act: number;
        include_affinity: boolean;
    }) => Promise<{
        content: {
            type: string;
            text: string;
        }[];
    }>;
})[];
//# sourceMappingURL=character-tools.d.ts.map