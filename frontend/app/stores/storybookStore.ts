import { create } from "zustand";
import { Scene } from "../lib/types";

interface StorybookStore {
  readonly storybookId: string | null;
  readonly scenes: readonly Scene[];
  setStorybookId: (id: string) => void;
  addScene: (scene: Scene) => void;
  updateSceneImage: (sceneId: string, imageUrl: string) => void;
  updateSceneVideo: (sceneId: string, videoUrl: string) => void;
  updateSceneTTS: (sceneId: string, audioUrl: string) => void;
  updateSceneStatus: (sceneId: string, status: Scene["status"]) => void;
  updateSceneNarration: (sceneId: string, narrationText: string) => void;
  loadScenes: (scenes: readonly Scene[]) => void;
  clear: () => void;
}

export const useStorybookStore = create<StorybookStore>((set) => ({
  storybookId: null,
  scenes: [],

  setStorybookId: (id) => set({ storybookId: id }),

  addScene: (scene) => set((state) => ({ scenes: [...state.scenes, scene] })),

  updateSceneImage: (sceneId, imageUrl) =>
    set((state) => ({
      scenes: state.scenes.map((s) =>
        s.id === sceneId ? { ...s, imageUrl, status: "ready" as const } : s,
      ),
    })),

  updateSceneVideo: (sceneId, videoUrl) =>
    set((state) => ({
      scenes: state.scenes.map((s) =>
        s.id === sceneId ? { ...s, videoUrl } : s,
      ),
    })),

  updateSceneTTS: (sceneId, audioUrl) =>
    set((state) => ({
      scenes: state.scenes.map((s) =>
        s.id === sceneId ? { ...s, audioUrl } : s,
      ),
    })),

  updateSceneStatus: (sceneId, status) =>
    set((state) => ({
      scenes: state.scenes.map((s) =>
        s.id === sceneId ? { ...s, status } : s,
      ),
    })),

  updateSceneNarration: (sceneId, narrationText) =>
    set((state) => ({
      scenes: state.scenes.map((s) =>
        s.id === sceneId ? { ...s, narrationText } : s,
      ),
    })),

  loadScenes: (scenes) => set({ scenes }),

  clear: () => set({ storybookId: null, scenes: [] }),
}));
