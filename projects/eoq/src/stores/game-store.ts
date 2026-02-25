import { create } from "zustand";
import type {
  Character,
  DialogueTurn,
  GameSession,
  WorldState,
} from "@/types/game";

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
  /** Mock mode — use pre-recorded responses instead of LLM */
  mockMode: boolean;

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
  setMockMode: (mock: boolean) => void;
}

export const useGameStore = create<GameState>((set) => ({
  session: null,
  isGenerating: false,
  isGeneratingImage: false,
  streamingText: "",
  backgroundUrl: null,
  portraitUrl: null,
  mockMode: process.env.NODE_ENV === "development",

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

  setMockMode: (mock) => set({ mockMode: mock }),
}));
