"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useStorybookStore } from "../stores/storybookStore";
import { useUIStore } from "../stores/uiStore";
import { SceneCard } from "./SceneCard";

export function SceneStrip() {
  const scenes = useStorybookStore((s) => s.scenes);
  const selectedSceneId = useUIStore((s) => s.selectedSceneId);
  const selectScene = useUIStore((s) => s.selectScene);
  const openPlayer = useUIStore((s) => s.openPlayer);
  const hasReadyScenes = scenes.some((s) => s.status === "ready");

  return (
    <AnimatePresence>
      {scenes.length > 0 && (
        <motion.div
          className="border-b border-border-subtle bg-bg-surface/30"
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.4, ease: "easeOut" }}
        >
          <div className="flex items-center gap-3 overflow-x-auto px-4 py-3 snap-x snap-mandatory">
            {scenes.map((scene) => (
              <SceneCard
                key={scene.id}
                scene={scene}
                size="compact"
                isSelected={scene.id === selectedSceneId}
                onClick={() => selectScene(scene.id)}
              />
            ))}

            {hasReadyScenes && (
              <button
                onClick={openPlayer}
                className="flex-shrink-0 flex items-center gap-1.5 rounded-lg border border-accent-cyan/30 bg-accent-cyan/5 px-3 py-2 font-display text-[10px] text-accent-cyan hover:bg-accent-cyan/10 transition-colors"
              >
                <svg
                  className="h-3.5 w-3.5"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M8 5v14l11-7z" />
                </svg>
                Play
              </button>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
