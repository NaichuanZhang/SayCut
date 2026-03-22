import { create } from "zustand";
import { AgentState } from "../lib/types";

interface UIStore {
  readonly agentState: AgentState;
  readonly isRecording: boolean;
  readonly selectedSceneId: string | null;
  readonly isPlayerOpen: boolean;
  readonly isAgentPanelOpen: boolean;
  setAgentState: (state: AgentState) => void;
  setRecording: (val: boolean) => void;
  selectScene: (id: string | null) => void;
  openPlayer: () => void;
  closePlayer: () => void;
  toggleAgentPanel: () => void;
}

export const useUIStore = create<UIStore>((set) => ({
  agentState: "idle",
  isRecording: false,
  selectedSceneId: null,
  isPlayerOpen: false,
  isAgentPanelOpen: true,

  setAgentState: (agentState) => set({ agentState }),
  setRecording: (isRecording) => set({ isRecording }),
  selectScene: (id) => set({ selectedSceneId: id }),
  openPlayer: () => set({ isPlayerOpen: true }),
  closePlayer: () => set({ isPlayerOpen: false }),
  toggleAgentPanel: () =>
    set((state) => ({ isAgentPanelOpen: !state.isAgentPanelOpen })),
}));
