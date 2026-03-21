"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import clsx from "clsx";
import { useUIStore } from "../stores/uiStore";
import { useStorybookStore } from "../stores/storybookStore";
import { SayCutLogo } from "./SayCutLogo";

const SCENE_DURATION = 6000; // ms per scene
const FADE_DURATION = 1000;

export function PlayerOverlay() {
  const isPlayerOpen = useUIStore((s) => s.isPlayerOpen);
  const closePlayer = useUIStore((s) => s.closePlayer);
  const scenes = useStorybookStore((s) => s.scenes);
  const readyScenes = scenes.filter((s) => s.status === "ready");

  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPaused, setIsPaused] = useState(false);

  useEffect(() => {
    if (!isPlayerOpen) {
      setCurrentIndex(0);
      setIsPaused(false);
    }
  }, [isPlayerOpen]);

  useEffect(() => {
    if (!isPlayerOpen || isPaused || readyScenes.length === 0) return;

    const timer = setTimeout(() => {
      if (currentIndex < readyScenes.length - 1) {
        setCurrentIndex((i) => i + 1);
      } else {
        closePlayer();
      }
    }, SCENE_DURATION);

    return () => clearTimeout(timer);
  }, [isPlayerOpen, isPaused, currentIndex, readyScenes.length, closePlayer]);

  const togglePause = useCallback(() => setIsPaused((p) => !p), []);
  const currentScene = readyScenes[currentIndex];

  return (
    <AnimatePresence>
      {isPlayerOpen && currentScene && (
        <motion.div
          className="fixed inset-0 z-[60] bg-black flex flex-col"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Subtle top-left wordmark */}
          <div className="absolute top-4 left-4 z-20">
            <SayCutLogo
              size="sm"
              variant="wordmark"
              className="text-white/30 hover:text-white/30"
            />
          </div>

          {/* Close button */}
          <button
            onClick={closePlayer}
            className="absolute top-4 right-4 z-20 h-10 w-10 rounded-full bg-white/10 backdrop-blur-sm flex items-center justify-center text-white/70 hover:text-white transition-colors"
            aria-label="Close player"
          >
            <svg
              className="h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>

          {/* Scene image with crossfade */}
          <div className="flex-1 relative overflow-hidden">
            <AnimatePresence mode="wait">
              <motion.div
                key={currentScene.id}
                className="absolute inset-0"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: FADE_DURATION / 1000 }}
              >
                {currentScene.imageUrl && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={currentScene.imageUrl}
                    alt={currentScene.title}
                    className="w-full h-full object-contain"
                  />
                )}
              </motion.div>
            </AnimatePresence>

            {/* Letterbox bars */}
            <div className="absolute top-0 left-0 right-0 h-16 bg-gradient-to-b from-black to-transparent" />
            <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-black to-transparent" />
          </div>

          {/* Narration text (subtitle style) */}
          <div className="absolute bottom-20 left-0 right-0 px-8">
            <AnimatePresence mode="wait">
              <motion.p
                key={currentScene.id}
                className="text-center text-base text-white/90 max-w-2xl mx-auto leading-relaxed"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.4 }}
              >
                {currentScene.narrationText}
              </motion.p>
            </AnimatePresence>
          </div>

          {/* Controls bar */}
          <div className="absolute bottom-4 left-0 right-0 flex flex-col items-center gap-3">
            {/* Pause/play */}
            <button
              onClick={togglePause}
              className="h-10 w-10 rounded-full bg-white/10 backdrop-blur-sm flex items-center justify-center text-white/70 hover:text-white transition-colors"
              aria-label={isPaused ? "Play" : "Pause"}
            >
              {isPaused ? (
                <svg
                  className="h-5 w-5 ml-0.5"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M8 5v14l11-7z" />
                </svg>
              ) : (
                <svg
                  className="h-5 w-5"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <rect x="6" y="4" width="4" height="16" rx="1" />
                  <rect x="14" y="4" width="4" height="16" rx="1" />
                </svg>
              )}
            </button>

            {/* Progress dots */}
            <div className="flex gap-2">
              {readyScenes.map((scene, i) => (
                <button
                  key={scene.id}
                  onClick={() => setCurrentIndex(i)}
                  className={clsx(
                    "h-2 rounded-full transition-all duration-300",
                    i === currentIndex
                      ? "w-6 bg-accent-cyan"
                      : "w-2 bg-white/30 hover:bg-white/50",
                  )}
                  aria-label={`Go to scene ${i + 1}`}
                />
              ))}
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
