import { create } from "zustand";
import type {
  Character,
  DialogueTurn,
  GameSession,
  WorldState,
  RivalryTension,
  PhoneMessage,
  LegacyDaughter,
} from "@/types/game";

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
  /** Mark a character's Awakening as fired and apply resistance ceiling drop */
  fireAwakening: (characterId: string, newResistanceCeiling: number) => void;
  /** Trigger a character's stripper arc return */
  triggerStripperArc: (characterId: string) => void;
  /** Update rivalry tension between two queens */
  updateRivalryTension: (queenAId: string, queenBId: string, delta: number) => void;
  /** Mark a Harem Wars event as fired */
  markHaremWarsEventFired: (queenAId: string, queenBId: string, eventId: string) => void;
  /** Add a phone message to the pending queue */
  addPhoneMessage: (message: PhoneMessage) => void;
  /** Dismiss/read a phone message */
  dismissPhoneMessage: (characterId: string, day: number) => void;
  /** Add a Legacy daughter */
  addLegacyDaughter: (daughter: LegacyDaughter) => void;
  /** Toggle No Mercy mode */
  togglePlayMode: () => void;
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

  fireAwakening: (characterId, newResistanceCeiling) =>
    set((state) => {
      if (!state.session) return state;
      const char = state.session.characters[characterId];
      if (!char) return state;
      return {
        session: {
          ...state.session,
          characters: {
            ...state.session.characters,
            [characterId]: {
              ...char,
              awakeningFired: true,
              resistanceCeiling: newResistanceCeiling,
              // Cap current resistance at new ceiling
              resistance: Math.min(char.resistance, newResistanceCeiling),
              // Trigger stripper arc
              stripperArc: char.stripperArc
                ? { ...char.stripperArc, triggered: true }
                : char.stripperArc,
            },
          },
          worldState: {
            ...state.session.worldState,
            plotFlags: {
              ...state.session.worldState.plotFlags,
              [`awakening_fired_${characterId}`]: true,
            },
          },
        },
      };
    }),

  triggerStripperArc: (characterId) =>
    set((state) => {
      if (!state.session) return state;
      const char = state.session.characters[characterId];
      if (!char?.stripperArc) return state;
      return {
        session: {
          ...state.session,
          characters: {
            ...state.session.characters,
            [characterId]: {
              ...char,
              stripperArc: { ...char.stripperArc, triggered: true },
            },
          },
          worldState: {
            ...state.session.worldState,
            plotFlags: {
              ...state.session.worldState.plotFlags,
              [`stripper_arc_triggered_${characterId}`]: true,
            },
          },
        },
      };
    }),

  updateRivalryTension: (queenAId, queenBId, delta) =>
    set((state) => {
      if (!state.session) return state;
      const tensions = [...state.session.worldState.rivalryTensions];
      const idx = tensions.findIndex(
        (t) =>
          (t.queenAId === queenAId && t.queenBId === queenBId) ||
          (t.queenAId === queenBId && t.queenBId === queenAId)
      );
      if (idx >= 0) {
        tensions[idx] = {
          ...tensions[idx],
          tension: Math.max(0, Math.min(100, tensions[idx].tension + delta)),
        };
      } else {
        tensions.push({
          queenAId,
          queenBId,
          tension: Math.max(0, Math.min(100, delta)),
          firedEvents: [],
        });
      }
      return {
        session: {
          ...state.session,
          worldState: { ...state.session.worldState, rivalryTensions: tensions },
        },
      };
    }),

  markHaremWarsEventFired: (queenAId, queenBId, eventId) =>
    set((state) => {
      if (!state.session) return state;
      const tensions = state.session.worldState.rivalryTensions.map((t) => {
        if (
          (t.queenAId === queenAId && t.queenBId === queenBId) ||
          (t.queenAId === queenBId && t.queenBId === queenAId)
        ) {
          return { ...t, firedEvents: [...t.firedEvents, eventId] };
        }
        return t;
      });
      return {
        session: {
          ...state.session,
          worldState: { ...state.session.worldState, rivalryTensions: tensions },
        },
      };
    }),

  addPhoneMessage: (message) =>
    set((state) => {
      if (!state.session) return state;
      return {
        session: {
          ...state.session,
          worldState: {
            ...state.session.worldState,
            pendingPhoneMessages: [
              ...state.session.worldState.pendingPhoneMessages,
              message,
            ],
          },
        },
      };
    }),

  dismissPhoneMessage: (characterId, day) =>
    set((state) => {
      if (!state.session) return state;
      return {
        session: {
          ...state.session,
          worldState: {
            ...state.session.worldState,
            pendingPhoneMessages: state.session.worldState.pendingPhoneMessages.filter(
              (m) => !(m.characterId === characterId && m.day === day)
            ),
          },
        },
      };
    }),

  addLegacyDaughter: (daughter) =>
    set((state) => {
      if (!state.session) return state;
      return {
        session: {
          ...state.session,
          worldState: {
            ...state.session.worldState,
            legacyDaughters: [
              ...state.session.worldState.legacyDaughters,
              daughter,
            ],
          },
        },
      };
    }),

  togglePlayMode: () =>
    set((state) => {
      if (!state.session) return state;
      const current = state.session.worldState.playMode;
      return {
        session: {
          ...state.session,
          worldState: {
            ...state.session.worldState,
            playMode: current === "blissful" ? "no_mercy" : "blissful",
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
