import { create } from "zustand";
import type {
  Character,
  DialogueTurn,
  GameSession,
  PlayerStyle,
  WorldState,
} from "@/types/game";
import { classifyChoiceStyle, DEFAULT_PLAYER_STYLE } from "@/types/game";
import type { PlayerChoice } from "@/types/game";

const SAVE_KEY = "eoq-save";

interface GameState {
  /** Current game session (null if no game loaded) */
  session: GameSession | null;
  /** Whether the game is currently generating dialogue */
  isGenerating: boolean;
  /** Whether the game is currently generating an image */
  isGeneratingImage: boolean;
  /** Current streaming text (partial dialogue being received) */
  streamingText: string;
  /** Current background image URL */
  backgroundUrl: string | null;
  /** Current character portrait URL */
  portraitUrl: string | null;
  /** Scenes the player has already visited (for intro tracking) */
  visitedScenes: Set<string>;
  /** Queen selector mode — when set, shows queen picker UI for multi-queen scenes */
  queenSelectorMode: "confrontation" | "banquet" | "duel" | null;

  // Actions
  setSession: (session: GameSession) => void;
  addDialogue: (turn: DialogueTurn) => void;
  setStreamingText: (text: string) => void;
  appendStreamingText: (chunk: string) => void;
  setGenerating: (generating: boolean) => void;
  setGeneratingImage: (generating: boolean) => void;
  setBackgroundUrl: (url: string | null) => void;
  setPortraitUrl: (url: string | null) => void;
  updateCharacter: (id: string, updates: Partial<Character>) => void;
  updateWorldState: (updates: Partial<WorldState>) => void;
  setPlotFlag: (flag: string, value: boolean) => void;
  setPlotFlags: (flags: Record<string, boolean>) => void;
  attachChoicesToLastTurn: (choices: import("@/types/game").PlayerChoice[]) => void;
  addInventoryItem: (item: string) => void;
  markSceneVisited: (sceneId: string) => void;
  setQueenSelectorMode: (mode: "confrontation" | "banquet" | "duel" | null) => void;
  trackChoice: (choice: PlayerChoice) => void;
  saveGame: () => void;
  loadGame: () => boolean;
  clearSave: () => void;
}

export const useGameStore = create<GameState>((set, get) => ({
  session: null,
  isGenerating: false,
  isGeneratingImage: false,
  streamingText: "",
  backgroundUrl: null,
  portraitUrl: null,
  visitedScenes: new Set(),
  queenSelectorMode: null,

  setSession: (session) => set({ session }),

  addDialogue: (turn) =>
    set((state) => {
      if (!state.session) return state;
      return {
        session: {
          ...state.session,
          dialogueHistory: [...state.session.dialogueHistory, turn],
          lastPlayedAt: Date.now(),
        },
        streamingText: "",
      };
    }),

  setStreamingText: (text) => set({ streamingText: text }),
  appendStreamingText: (chunk) =>
    set((state) => ({ streamingText: state.streamingText + chunk })),

  setGenerating: (generating) => set({ isGenerating: generating }),
  setGeneratingImage: (generating) => set({ isGeneratingImage: generating }),
  setBackgroundUrl: (url) => set({ backgroundUrl: url }),
  setPortraitUrl: (url) => set({ portraitUrl: url }),

  updateCharacter: (id, updates) =>
    set((state) => {
      if (!state.session) return state;
      const char = state.session.characters[id];
      if (!char) return state;
      return {
        session: {
          ...state.session,
          characters: {
            ...state.session.characters,
            [id]: { ...char, ...updates },
          },
        },
      };
    }),

  updateWorldState: (updates) =>
    set((state) => {
      if (!state.session) return state;
      return {
        session: {
          ...state.session,
          worldState: { ...state.session.worldState, ...updates },
        },
      };
    }),

  setPlotFlag: (flag, value) =>
    set((state) => {
      if (!state.session) return state;
      return {
        session: {
          ...state.session,
          worldState: {
            ...state.session.worldState,
            plotFlags: {
              ...state.session.worldState.plotFlags,
              [flag]: value,
            },
          },
        },
      };
    }),

  setPlotFlags: (flags) =>
    set((state) => {
      if (!state.session) return state;
      return {
        session: {
          ...state.session,
          worldState: {
            ...state.session.worldState,
            plotFlags: {
              ...state.session.worldState.plotFlags,
              ...flags,
            },
          },
        },
      };
    }),

  addInventoryItem: (item) =>
    set((state) => {
      if (!state.session) return state;
      if (state.session.worldState.inventory.includes(item)) return state;
      return {
        session: {
          ...state.session,
          worldState: {
            ...state.session.worldState,
            inventory: [...state.session.worldState.inventory, item],
          },
        },
      };
    }),

  attachChoicesToLastTurn: (choices) =>
    set((state) => {
      if (!state.session) return state;
      const history = [...state.session.dialogueHistory];
      if (history.length === 0) return state;
      history[history.length - 1] = { ...history[history.length - 1], choices };
      return {
        session: { ...state.session, dialogueHistory: history },
      };
    }),

  markSceneVisited: (sceneId) =>
    set((state) => {
      const visited = new Set(state.visitedScenes);
      visited.add(sceneId);
      return { visitedScenes: visited };
    }),

  setQueenSelectorMode: (mode) => set({ queenSelectorMode: mode }),

  trackChoice: (choice) =>
    set((state) => {
      if (!state.session) return state;
      const style = { ...state.session.playerStyle };
      const deltas = classifyChoiceStyle(choice);
      const n = style.totalChoices + 1;
      // Weighted running average — new choices blend into existing scores
      const blend = (current: number, delta: number | undefined) => {
        if (delta == null) return current;
        const raw = current + (delta - current) / n;
        return Math.max(0, Math.min(100, raw));
      };
      return {
        session: {
          ...state.session,
          playerStyle: {
            mercyScore: blend(style.mercyScore, deltas.mercyScore != null ? style.mercyScore + deltas.mercyScore : undefined),
            seductionScore: blend(style.seductionScore, deltas.seductionScore != null ? style.seductionScore + deltas.seductionScore : undefined),
            manipulationScore: blend(style.manipulationScore, deltas.manipulationScore != null ? style.manipulationScore + deltas.manipulationScore : undefined),
            dominanceScore: blend(style.dominanceScore, deltas.dominanceScore != null ? style.dominanceScore + deltas.dominanceScore : undefined),
            diplomacyScore: blend(style.diplomacyScore, deltas.diplomacyScore != null ? style.diplomacyScore + deltas.diplomacyScore : undefined),
            totalChoices: n,
          },
        },
      };
    }),

  saveGame: () => {
    const { session, visitedScenes } = get();
    if (!session) return;
    try {
      const data = {
        session,
        visitedScenes: Array.from(visitedScenes),
      };
      localStorage.setItem(SAVE_KEY, JSON.stringify(data));
    } catch {
      // localStorage may be full or unavailable
    }
  },

  loadGame: () => {
    try {
      const raw = localStorage.getItem(SAVE_KEY);
      if (!raw) return false;
      const data = JSON.parse(raw);
      if (!data.session) return false;
      // Backfill playerStyle for saves from before this feature
      if (!data.session.playerStyle) {
        data.session.playerStyle = { ...DEFAULT_PLAYER_STYLE };
      }
      set({
        session: data.session,
        visitedScenes: new Set(data.visitedScenes ?? []),
      });
      return true;
    } catch {
      return false;
    }
  },

  clearSave: () => {
    try {
      localStorage.removeItem(SAVE_KEY);
    } catch {
      // ignore
    }
    set({ session: null, visitedScenes: new Set() });
  },
}));
