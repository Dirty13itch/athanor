import { z } from "zod";
import { HSceneConfig, IntensityLevel } from "../types.js";
export declare const sceneToolDefs: ({
    name: string;
    description: string;
    inputSchema: z.ZodObject<{
        file_path: z.ZodString;
        label: z.ZodString;
        background: z.ZodString;
        music: z.ZodOptional<z.ZodString>;
        characters: z.ZodDefault<z.ZodOptional<z.ZodArray<z.ZodString, "many">>>;
        transition: z.ZodDefault<z.ZodOptional<z.ZodString>>;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        label: string;
        background: string;
        characters: string[];
        transition: string;
        music?: string | undefined;
    }, {
        file_path: string;
        label: string;
        background: string;
        music?: string | undefined;
        characters?: string[] | undefined;
        transition?: string | undefined;
    }>;
    handler: (args: {
        file_path: string;
        label: string;
        background: string;
        music?: string;
        characters: string[];
        transition: string;
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
        transition: z.ZodEnum<["dissolve", "fade", "blinds", "squares", "pixellate", "wipeleft", "wiperight", "wipeup", "wipedown", "flipvertical", "fliphorizontal"]>;
        after_label: z.ZodOptional<z.ZodString>;
        custom_time: z.ZodOptional<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        transition: "dissolve" | "fade" | "blinds" | "squares" | "pixellate" | "wipeleft" | "wiperight" | "wipeup" | "wipedown" | "flipvertical" | "fliphorizontal";
        after_label?: string | undefined;
        custom_time?: number | undefined;
    }, {
        file_path: string;
        transition: "dissolve" | "fade" | "blinds" | "squares" | "pixellate" | "wipeleft" | "wiperight" | "wipeup" | "wipedown" | "flipvertical" | "fliphorizontal";
        after_label?: string | undefined;
        custom_time?: number | undefined;
    }>;
    handler: (args: {
        file_path: string;
        transition: string;
        after_label?: string;
        custom_time?: number;
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
        action: z.ZodEnum<["show", "hide"]>;
        image: z.ZodString;
        at: z.ZodOptional<z.ZodString>;
        transition: z.ZodOptional<z.ZodString>;
        after_label: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        image: string;
        action: "show" | "hide";
        at?: string | undefined;
        after_label?: string | undefined;
        transition?: string | undefined;
    }, {
        file_path: string;
        image: string;
        action: "show" | "hide";
        at?: string | undefined;
        after_label?: string | undefined;
        transition?: string | undefined;
    }>;
    handler: (args: {
        file_path: string;
        action: "show" | "hide";
        image: string;
        at?: string;
        transition?: string;
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
        name: z.ZodString;
        frames: z.ZodArray<z.ZodObject<{
            image: z.ZodString;
            delay: z.ZodNumber;
        }, "strip", z.ZodTypeAny, {
            image: string;
            delay: number;
        }, {
            image: string;
            delay: number;
        }>, "many">;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        name: string;
        frames: {
            image: string;
            delay: number;
        }[];
    }, {
        file_path: string;
        name: string;
        frames: {
            image: string;
            delay: number;
        }[];
    }>;
    handler: (args: {
        file_path: string;
        name: string;
        frames: {
            image: string;
            delay: number;
        }[];
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
        file: z.ZodString;
        fadeout: z.ZodOptional<z.ZodNumber>;
        fadein: z.ZodOptional<z.ZodNumber>;
        channel: z.ZodDefault<z.ZodOptional<z.ZodEnum<["music", "ambient", "voice"]>>>;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        file: string;
        channel: "music" | "ambient" | "voice";
        fadeout?: number | undefined;
        fadein?: number | undefined;
    }, {
        file_path: string;
        file: string;
        fadeout?: number | undefined;
        fadein?: number | undefined;
        channel?: "music" | "ambient" | "voice" | undefined;
    }>;
    handler: (args: {
        file_path: string;
        file: string;
        fadeout?: number;
        fadein?: number;
        channel: string;
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
        sound_file: z.ZodString;
        channel: z.ZodDefault<z.ZodOptional<z.ZodString>>;
        after_label: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        channel: string;
        sound_file: string;
        after_label?: string | undefined;
    }, {
        file_path: string;
        sound_file: string;
        after_label?: string | undefined;
        channel?: string | undefined;
    }>;
    handler: (args: {
        file_path: string;
        sound_file: string;
        channel: string;
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
        cg_id: z.ZodString;
        cg_image: z.ZodString;
        unlock_condition: z.ZodString;
        background_music: z.ZodOptional<z.ZodString>;
        caption: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        cg_id: string;
        cg_image: string;
        unlock_condition: string;
        background_music?: string | undefined;
        caption?: string | undefined;
    }, {
        file_path: string;
        cg_id: string;
        cg_image: string;
        unlock_condition: string;
        background_music?: string | undefined;
        caption?: string | undefined;
    }>;
    handler: (args: {
        file_path: string;
        cg_id: string;
        cg_image: string;
        unlock_condition: string;
        background_music?: string;
        caption?: string;
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
        character_id: z.ZodString;
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
        intensity: z.ZodEnum<["soft", "medium", "explicit", "extreme"]>;
        corruption_stage: z.ZodNumber;
        acts: z.ZodArray<z.ZodObject<{
            id: z.ZodString;
            description: z.ZodString;
            dialogue_count: z.ZodNumber;
            has_cg: z.ZodBoolean;
        }, "strip", z.ZodTypeAny, {
            description: string;
            id: string;
            dialogue_count: number;
            has_cg: boolean;
        }, {
            description: string;
            id: string;
            dialogue_count: number;
            has_cg: boolean;
        }>, "many">;
        unlock_condition: z.ZodOptional<z.ZodString>;
        cg_prefix: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        label: string;
        character_id: string;
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
        acts: {
            description: string;
            id: string;
            dialogue_count: number;
            has_cg: boolean;
        }[];
        intensity: "soft" | "medium" | "explicit" | "extreme";
        corruption_stage: number;
        unlock_condition?: string | undefined;
        cg_prefix?: string | undefined;
    }, {
        file_path: string;
        label: string;
        character_id: string;
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
        acts: {
            description: string;
            id: string;
            dialogue_count: number;
            has_cg: boolean;
        }[];
        intensity: "soft" | "medium" | "explicit" | "extreme";
        corruption_stage: number;
        unlock_condition?: string | undefined;
        cg_prefix?: string | undefined;
    }>;
    handler: (args: {
        file_path: string;
        label: string;
        character_id: string;
        dna: HSceneConfig["dna"];
        intensity: IntensityLevel;
        corruption_stage: number;
        acts: HSceneConfig["acts"];
        unlock_condition?: string;
        cg_prefix?: string;
    }) => Promise<{
        content: {
            type: string;
            text: string;
        }[];
    }>;
})[];
//# sourceMappingURL=scene-tools.d.ts.map