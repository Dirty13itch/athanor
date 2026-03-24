import { CharacterDNA, RenpyCharacterDef, LayeredImageConfig, ATLTransform, ScreenDef, ChoiceOption, HSceneConfig, CorruptionStage, EndingConfig, AffinityConfig, PhoneMessage } from "./types.js";
export declare function indent(lines: string[], spaces?: number): string;
export declare function block(...lines: string[]): string;
export declare function fileHeader(description: string): string;
export declare function generateCharacterDef(def: RenpyCharacterDef): string;
export declare function generateCharacterFromDNA(dna: CharacterDNA): string;
export declare function generateLayeredImage(config: LayeredImageConfig): string;
export declare function generateLabel(name: string, body: string[]): string;
export declare function generateDialogue(speaker: string, text: string, tag?: string): string;
export declare function generateNarration(text: string): string;
export declare function generateChoiceMenu(prompt: string, options: ChoiceOption[]): string;
export declare function generateScene(background: string, transition?: string): string;
export declare function generateShow(image: string, at?: string, transition?: string): string;
export declare function generateHide(image: string, transition?: string): string;
export declare function generatePlayMusic(file: string, fadeout?: number, fadein?: number): string;
export declare function generatePlaySound(file: string, channel?: string): string;
export declare function generateTransition(name: string): string;
export declare function generateATLTransform(t: ATLTransform): string;
export declare function generateATLAnimation(name: string, frames: {
    image: string;
    delay: number;
}[]): string;
export declare function generateScreen(def: ScreenDef): string;
export declare function generateDefault(name: string, value: string): string;
export declare function generateDefine(name: string, value: string): string;
export declare function generateConditionBlock(conditions: {
    condition: string;
    body: string[];
}[], else_body?: string[]): string;
export declare function generatePythonBlock(code: string): string;
export declare function generateAffinityDefaults(cfg: AffinityConfig): string;
export declare function generateAffinityCheck(variable: string, character_id: string): string;
export declare function generateHScene(cfg: HSceneConfig): string;
export declare function generateCorruptionArc(queen_id: string, stages: CorruptionStage[]): string;
export declare function generateEnding(cfg: EndingConfig): string;
export declare function generatePhoneMessages(msgs: PhoneMessage[]): string;
export declare function generateGalleryEntry(id: string, name: string, image: string, unlock_condition: string, thumbnail?: string): string;
export declare function generateAchievement(id: string, name: string, description: string, icon?: string, points?: number): string;
export declare function generateProjectOptions(config: {
    name: string;
    build_name: string;
    version: string;
    developer: string;
    copyright: string;
}): string;
export interface FlowNode {
    label: string;
    jumps: string[];
    calls: string[];
    menus: {
        prompt: string;
        options: string[];
    }[];
}
export declare function parseFlowchart(script: string): FlowNode[];
export declare function renderFlowchartDot(nodes: FlowNode[]): string;
export declare function extractTranslatableStrings(script: string): string[];
export declare function mergeScripts(a: string, b: string): string;
export interface ValidationResult {
    valid: boolean;
    errors: string[];
    warnings: string[];
}
export declare function validateScript(script: string): ValidationResult;
//# sourceMappingURL=renpy-generator.d.ts.map