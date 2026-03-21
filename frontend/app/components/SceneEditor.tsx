"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import clsx from "clsx";
import { useStorybookStore } from "../stores/storybookStore";
import { useUIStore } from "../stores/uiStore";
import { useAudioPlayback } from "../hooks/useAudioPlayback";
import { SayCutLogo } from "./SayCutLogo";

export function SceneEditor() {
  const scenes = useStorybookStore((s) => s.scenes);
  const selectedSceneId = useUIStore((s) => s.selectedSceneId);
  const updateSceneNarration = useStorybookStore((s) => s.updateSceneNarration);
  const { play, pause, isPlaying } = useAudioPlayback();

  const scene = scenes.find((s) => s.id === selectedSceneId);
  const [localText, setLocalText] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  // Sync local text when scene changes
  useEffect(() => {
    setLocalText(scene?.narrationText ?? "");
  }, [scene?.id, scene?.narrationText]);

  const handleTextChange = useCallback(
    (value: string) => {
      setLocalText(value);
      if (!scene) return;
      clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        updateSceneNarration(scene.id, value);
      }, 300);
    },
    [scene, updateSceneNarration],
  );

  // Empty state
  if (!scene) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center max-w-sm">
          <div className="mx-auto mb-6 opacity-20">
            <SayCutLogo size="xl" variant="mark" />
          </div>
          <p className="font-display text-xs uppercase tracking-widest text-text-muted/50 mb-3">
            Voice-Powered Storyboards
          </p>
          <p className="text-sm text-text-muted">
            Hold the orb and tell the agent your story idea
          </p>
          <p className="text-xs text-text-muted/50 mt-1">
            Scenes will appear here as they are created
          </p>
        </div>
      </div>
    );
  }

  const isGenerating = scene.status === "generating";

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-3xl p-6 space-y-5">
        {/* Scene header */}
        <div className="flex items-baseline gap-3">
          <span className="font-display text-xs text-text-muted uppercase tracking-wider">
            Scene {scene.index + 1}
          </span>
          <h2 className="font-display text-lg text-text-primary">
            {scene.title}
          </h2>
        </div>

        {/* Image / Video preview */}
        <div className="aspect-video w-full rounded-xl overflow-hidden bg-bg-surface border border-border-subtle">
          {isGenerating && (
            <div
              className="w-full h-full flex items-center justify-center"
              style={{
                background:
                  "linear-gradient(90deg, var(--bg-surface) 25%, var(--bg-elevated) 50%, var(--bg-surface) 75%)",
                backgroundSize: "200% 100%",
                animation: "shimmer 1.5s ease-in-out infinite",
              }}
            >
              <span className="font-display text-sm text-accent-amber animate-pulse">
                Generating image...
              </span>
            </div>
          )}

          {scene.status === "ready" && scene.videoUrl && (
            <video
              src={scene.videoUrl}
              className="w-full h-full object-cover"
              autoPlay
              loop
              muted
              playsInline
            />
          )}

          {scene.status === "ready" && !scene.videoUrl && scene.imageUrl && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={scene.imageUrl}
              alt={scene.title}
              className="w-full h-full object-cover"
            />
          )}

          {scene.status === "empty" && (
            <div className="w-full h-full flex items-center justify-center">
              <span className="text-sm text-text-muted/40">
                Waiting for image
              </span>
            </div>
          )}
        </div>

        {/* Narration / Script text */}
        <div>
          <label className="block font-display text-xs text-text-muted uppercase tracking-wider mb-2">
            Narration
          </label>
          <textarea
            value={localText}
            onChange={(e) => handleTextChange(e.target.value)}
            className={clsx(
              "w-full rounded-lg bg-bg-surface border border-border-subtle px-4 py-3",
              "text-sm leading-relaxed text-text-primary font-body",
              "resize-none focus:outline-none focus:ring-1 focus:ring-accent-cyan/50 focus:border-accent-cyan/30",
              "placeholder:text-text-muted/40",
            )}
            rows={4}
            placeholder="Narration text will appear here..."
          />
        </div>

        {/* Audio controls */}
        <div>
          <label className="block font-display text-xs text-text-muted uppercase tracking-wider mb-2">
            Audio
          </label>
          <div className="flex items-center gap-3 rounded-lg bg-bg-surface border border-border-subtle px-4 py-3">
            <button
              onClick={() => {
                if (scene.audioUrl) {
                  isPlaying ? pause() : play(scene.audioUrl);
                }
              }}
              disabled={!scene.audioUrl}
              className={clsx(
                "h-8 w-8 rounded-full flex items-center justify-center flex-shrink-0 transition-colors",
                scene.audioUrl
                  ? "bg-accent-cyan/10 text-accent-cyan hover:bg-accent-cyan/20"
                  : "bg-bg-elevated text-text-muted/30 cursor-not-allowed",
              )}
              aria-label={isPlaying ? "Pause" : "Play"}
            >
              {isPlaying ? (
                <svg
                  className="h-4 w-4"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <rect x="6" y="4" width="4" height="16" rx="1" />
                  <rect x="14" y="4" width="4" height="16" rx="1" />
                </svg>
              ) : (
                <svg
                  className="h-4 w-4 ml-0.5"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M8 5v14l11-7z" />
                </svg>
              )}
            </button>

            {/* Progress bar placeholder */}
            <div className="flex-1 h-1 rounded-full bg-bg-elevated">
              {scene.audioUrl && (
                <div className="h-full w-0 rounded-full bg-accent-cyan transition-all" />
              )}
            </div>

            <span className="font-display text-[10px] text-text-muted">
              {scene.audioUrl ? "0:00" : "No audio"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
