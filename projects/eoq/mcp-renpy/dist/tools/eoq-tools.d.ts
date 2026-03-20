import { z } from "zod";
import { CharacterDNA, EndingType, PhoneMessage, IntensityLevel } from "../types.js";
export declare const eoqToolDefs: ({
    name: string;
    description: string;
    inputSchema: z.ZodObject<{
        output_dir: z.ZodString;
        queen_id: z.ZodString;
        queen_name: z.ZodString;
        archetype: z.ZodEnum<["ice_queen", "fire_dancer", "corrupted_saint", "dark_empress", "fallen_angel", "cursed_oracle"]>;
        color_hex: z.ZodString;
        kink_profile: z.ZodArray<z.ZodString, "many">;
        acts: z.ZodDefault<z.ZodNumber>;
        scenes_per_act: z.ZodDefault<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        archetype: "ice_queen" | "fire_dancer" | "corrupted_saint" | "dark_empress" | "fallen_angel" | "cursed_oracle";
        kink_profile: string[];
        color_hex: string;
        acts: number;
        scenes_per_act: number;
        output_dir: string;
        queen_id: string;
        queen_name: string;
    }, {
        archetype: "ice_queen" | "fire_dancer" | "corrupted_saint" | "dark_empress" | "fallen_angel" | "cursed_oracle";
        kink_profile: string[];
        color_hex: string;
        output_dir: string;
        queen_id: string;
        queen_name: string;
        acts?: number | undefined;
        scenes_per_act?: number | undefined;
    }>;
    handler: (args: {
        output_dir: string;
        queen_id: string;
        queen_name: string;
        archetype: string;
        color_hex: string;
        kink_profile: string[];
        acts: number;
        scenes_per_act: number;
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
        queen_id: z.ZodString;
        queen_name: z.ZodString;
        corruption_vector: z.ZodString;
        stage_descriptions: z.ZodArray<z.ZodString, "many">;
        intensities: z.ZodArray<z.ZodEnum<["soft", "medium", "explicit", "extreme"]>, "many">;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        corruption_vector: string;
        queen_id: string;
        queen_name: string;
        stage_descriptions: string[];
        intensities: ("soft" | "medium" | "explicit" | "extreme")[];
    }, {
        file_path: string;
        corruption_vector: string;
        queen_id: string;
        queen_name: string;
        stage_descriptions: string[];
        intensities: ("soft" | "medium" | "explicit" | "extreme")[];
    }>;
    handler: (args: {
        file_path: string;
        queen_id: string;
        queen_name: string;
        corruption_vector: string;
        stage_descriptions: string[];
        intensities: IntensityLevel[];
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
        queens_present: z.ZodArray<z.ZodString, "many">;
        agenda: z.ZodString;
        player_choices: z.ZodArray<z.ZodObject<{
            text: z.ZodString;
            jump: z.ZodOptional<z.ZodString>;
            affinity_delta: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodNumber>>;
        }, "strip", z.ZodTypeAny, {
            text: string;
            jump?: string | undefined;
            affinity_delta?: Record<string, number> | undefined;
        }, {
            text: string;
            jump?: string | undefined;
            affinity_delta?: Record<string, number> | undefined;
        }>, "many">;
        tension_level: z.ZodNumber;
        background: z.ZodDefault<z.ZodOptional<z.ZodString>>;
        music: z.ZodDefault<z.ZodOptional<z.ZodString>>;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        label: string;
        background: string;
        music: string;
        queens_present: string[];
        agenda: string;
        player_choices: {
            text: string;
            jump?: string | undefined;
            affinity_delta?: Record<string, number> | undefined;
        }[];
        tension_level: number;
    }, {
        file_path: string;
        label: string;
        queens_present: string[];
        agenda: string;
        player_choices: {
            text: string;
            jump?: string | undefined;
            affinity_delta?: Record<string, number> | undefined;
        }[];
        tension_level: number;
        background?: string | undefined;
        music?: string | undefined;
    }>;
    handler: (args: {
        file_path: string;
        label: string;
        queens_present: string[];
        agenda: string;
        player_choices: {
            text: string;
            jump?: string;
            affinity_delta?: Record<string, number>;
        }[];
        tension_level: number;
        background: string;
        music: string;
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
        queen_id: z.ZodString;
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
        trigger: z.ZodString;
        manifestation_type: z.ZodEnum<["power", "memory", "vision", "possession"]>;
        scene_count: z.ZodDefault<z.ZodNumber>;
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
        queen_id: string;
        trigger: string;
        manifestation_type: "power" | "memory" | "vision" | "possession";
        scene_count: number;
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
        queen_id: string;
        trigger: string;
        manifestation_type: "power" | "memory" | "vision" | "possession";
        scene_count?: number | undefined;
    }>;
    handler: (args: {
        file_path: string;
        queen_id: string;
        dna: CharacterDNA;
        trigger: string;
        manifestation_type: string;
        scene_count: number;
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
        instigator: z.ZodString;
        target: z.ZodString;
        rivalry_type: z.ZodEnum<["jealousy", "dominance", "alliance_break", "sabotage"]>;
        player_side_choices: z.ZodArray<z.ZodObject<{
            text: z.ZodString;
            favors: z.ZodString;
            affinity_delta: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodNumber>>;
        }, "strip", z.ZodTypeAny, {
            text: string;
            favors: string;
            affinity_delta?: Record<string, number> | undefined;
        }, {
            text: string;
            favors: string;
            affinity_delta?: Record<string, number> | undefined;
        }>, "many">;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        label: string;
        target: string;
        instigator: string;
        rivalry_type: "dominance" | "jealousy" | "alliance_break" | "sabotage";
        player_side_choices: {
            text: string;
            favors: string;
            affinity_delta?: Record<string, number> | undefined;
        }[];
    }, {
        file_path: string;
        label: string;
        target: string;
        instigator: string;
        rivalry_type: "dominance" | "jealousy" | "alliance_break" | "sabotage";
        player_side_choices: {
            text: string;
            favors: string;
            affinity_delta?: Record<string, number> | undefined;
        }[];
    }>;
    handler: (args: {
        file_path: string;
        label: string;
        instigator: string;
        target: string;
        rivalry_type: string;
        player_side_choices: {
            text: string;
            favors: string;
            affinity_delta?: Record<string, number>;
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
        queen_id: z.ZodString;
        messages: z.ZodArray<z.ZodObject<{
            timestamp_label: z.ZodString;
            messages: z.ZodArray<z.ZodString, "many">;
            attachment: z.ZodOptional<z.ZodString>;
            obsession_level: z.ZodNumber;
        }, "strip", z.ZodTypeAny, {
            timestamp_label: string;
            messages: string[];
            obsession_level: number;
            attachment?: string | undefined;
        }, {
            timestamp_label: string;
            messages: string[];
            obsession_level: number;
            attachment?: string | undefined;
        }>, "many">;
    }, "strip", z.ZodTypeAny, {
        file_path: string;
        queen_id: string;
        messages: {
            timestamp_label: string;
            messages: string[];
            obsession_level: number;
            attachment?: string | undefined;
        }[];
    }, {
        file_path: string;
        queen_id: string;
        messages: {
            timestamp_label: string;
            messages: string[];
            obsession_level: number;
            attachment?: string | undefined;
        }[];
    }>;
    handler: (args: {
        file_path: string;
        queen_id: string;
        messages: PhoneMessage[];
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
        output_dir: z.ZodString;
        queen_id: z.ZodString;
        queen_name: z.ZodString;
        venue_name: z.ZodString;
        stages: z.ZodDefault<z.ZodNumber>;
        arc_direction: z.ZodEnum<["degradation", "empowerment", "ambiguous"]>;
    }, "strip", z.ZodTypeAny, {
        output_dir: string;
        queen_id: string;
        queen_name: string;
        venue_name: string;
        stages: number;
        arc_direction: "degradation" | "empowerment" | "ambiguous";
    }, {
        output_dir: string;
        queen_id: string;
        queen_name: string;
        venue_name: string;
        arc_direction: "degradation" | "empowerment" | "ambiguous";
        stages?: number | undefined;
    }>;
    handler: (args: {
        output_dir: string;
        queen_id: string;
        queen_name: string;
        venue_name: string;
        stages: number;
        arc_direction: string;
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
        output_dir: z.ZodString;
        queen_id: z.ZodOptional<z.ZodString>;
        ending_type: z.ZodEnum<["true_love", "corruption_complete", "harem_empress", "burned_out", "queen_ascendant", "mutual_destruction", "secret_escape", "bad_end"]>;
        title: z.ZodString;
        conditions: z.ZodArray<z.ZodString, "many">;
        description: z.ZodString;
        music: z.ZodOptional<z.ZodString>;
        cg: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        description: string;
        conditions: string[];
        title: string;
        output_dir: string;
        ending_type: "true_love" | "corruption_complete" | "harem_empress" | "burned_out" | "queen_ascendant" | "mutual_destruction" | "secret_escape" | "bad_end";
        cg?: string | undefined;
        music?: string | undefined;
        queen_id?: string | undefined;
    }, {
        description: string;
        conditions: string[];
        title: string;
        output_dir: string;
        ending_type: "true_love" | "corruption_complete" | "harem_empress" | "burned_out" | "queen_ascendant" | "mutual_destruction" | "secret_escape" | "bad_end";
        cg?: string | undefined;
        music?: string | undefined;
        queen_id?: string | undefined;
    }>;
    handler: (args: {
        output_dir: string;
        queen_id?: string;
        ending_type: EndingType;
        title: string;
        conditions: string[];
        description: string;
        music?: string;
        cg?: string;
    }) => Promise<{
        content: {
            type: string;
            text: string;
        }[];
    }>;
})[];
//# sourceMappingURL=eoq-tools.d.ts.map