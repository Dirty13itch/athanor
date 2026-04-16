// ============================================================
// Shared types for mcp-renpy
// ============================================================

export interface CharacterDNA {
  name: string;
  archetype: string;           // e.g. "ice_queen", "corrupted_saint", "fire_dancer"
  affinity_type: string;       // e.g. "obsession", "devotion", "rivalry"
  corruption_vector: string;   // e.g. "greed", "lust", "power", "grief"
  kink_profile: string[];      // trait list
  voice_style: string;         // e.g. "cold_formal", "breathy_intimate"
  color_hex: string;           // name color in dialogue
  sprite_style: string;        // e.g. "regal", "casual", "degraded"
}

export interface SceneConfig {
  label: string;
  background: string;
  music?: string;
  ambient?: string;
  characters: string[];
  transition?: string;
}

export interface ChoiceOption {
  text: string;
  jump?: string;
  condition?: string;
  affinity_delta?: Record<string, number>;
}

export interface EndingConfig {
  type: EndingType;
  label: string;
  conditions: string[];
  title: string;
  music?: string;
  cg?: string;
  description: string;
}

export type EndingType =
  | "true_love"
  | "corruption_complete"
  | "harem_empress"
  | "burned_out"
  | "queen_ascendant"
  | "mutual_destruction"
  | "secret_escape"
  | "bad_end";

export interface AffinityConfig {
  character_id: string;
  variable_name: string;
  thresholds: {
    low: number;
    medium: number;
    high: number;
    max: number;
  };
  route_unlock_threshold: number;
}

export interface CorruptionStage {
  stage: number;           // 1-5
  label: string;
  description: string;
  trigger_condition: string;
  scene_type: "dialogue" | "event" | "h_scene" | "cg";
  intensity: IntensityLevel;
}

export type IntensityLevel = "soft" | "medium" | "explicit" | "extreme";

export interface HSceneConfig {
  label: string;
  character_id: string;
  dna: CharacterDNA;
  intensity: IntensityLevel;
  corruption_stage: number;
  acts: HSceneAct[];
  unlock_condition?: string;
  cg_prefix?: string;
}

export interface HSceneAct {
  id: string;
  description: string;
  dialogue_count: number;
  has_cg: boolean;
}

export interface PhoneMessage {
  sender: string;
  timestamp_label: string;
  messages: string[];
  attachment?: string;
  obsession_level: number; // 1-5
}

export interface QueenRoute {
  queen_id: string;
  dna: CharacterDNA;
  acts: RouteAct[];
  corruption_arc: CorruptionStage[];
  endings: EndingConfig[];
  affinity: AffinityConfig;
}

export interface RouteAct {
  act_number: number;
  label_prefix: string;
  scenes: SceneConfig[];
  h_scenes: HSceneConfig[];
  affinity_required?: number;
  flags_required?: string[];
}

export interface RenpyCharacterDef {
  id: string;
  name: string;
  color: string;
  voice_tag?: string;
  what_font?: string;
  what_size?: number;
  image?: string;
  callback?: string;
}

export interface LayeredImageConfig {
  name: string;
  base?: string;
  attributes: LayeredImageAttribute[];
}

export interface LayeredImageAttribute {
  group: string;
  values: string[];
  default?: string;
}

export interface ATLTransform {
  name: string;
  body: string;
}

export interface ScreenDef {
  name: string;
  params?: string[];
  body: string;
}

export interface ProjectConfig {
  name: string;
  version: string;
  build_name: string;
  base_dir: string;
  game_dir: string;
  developer: string;
  copyright: string;
  ren_py_version: string;
}

export interface GalleryEntry {
  id: string;
  name: string;
  unlock_condition: string;
  image: string;
  thumbnail?: string;
}

export interface Achievement {
  id: string;
  name: string;
  description: string;
  condition: string;
  icon?: string;
  points?: number;
}

export interface CouncilScene {
  label: string;
  queens_present: string[];
  agenda: string;
  political_outcome: string;
  tension_level: number; // 1-5
}

export interface AwakeningEvent {
  queen_id: string;
  dna: CharacterDNA;
  trigger: string;
  manifestation_type: string; // "power", "memory", "vision", "possession"
  scenes: string[];
}

export interface HaremWarsEvent {
  instigator: string;
  target: string;
  rivalry_type: string; // "jealousy", "dominance", "alliance_break", "sabotage"
  player_choice: ChoiceOption[];
  consequence: string;
}

export interface StripperArc {
  queen_id: string;
  stage: number; // 1-7
  venue: string;
  audience_reaction: string;
  internal_monologue: string[];
  player_agency: string;
}
