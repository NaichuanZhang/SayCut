"use client";

import { motion } from "framer-motion";
import clsx from "clsx";
import { Scene } from "../lib/types";

interface SceneCardProps {
  readonly scene: Scene;
  readonly isSelected?: boolean;
  readonly size?: "default" | "compact";
  readonly onClick?: () => void;
}

export function SceneCard({
  scene,
  isSelected = false,
  size = "default",
  onClick,
}: SceneCardProps) {
  const widthClass = size === "compact" ? "w-28" : "w-48";

  return (
    <motion.button
      className={clsx(
        "relative flex-shrink-0 aspect-video rounded-lg overflow-hidden border transition-all",
        widthClass,
        "hover:scale-105 hover:shadow-lg hover:shadow-accent-cyan/10",
        isSelected && "ring-2 ring-accent-cyan ring-offset-2 ring-offset-bg-primary",
        scene.status === "empty" &&
          "border-dashed border-border-subtle bg-bg-surface",
        scene.status === "generating" && "border-accent-amber/30 bg-bg-surface",
        scene.status === "ready" && "border-border-subtle bg-bg-surface"
      )}
      onClick={onClick}
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
      aria-label={`Scene ${scene.index + 1}: ${scene.title}`}
    >
      {scene.status === "empty" && (
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xs text-text-muted font-display">
            {scene.index + 1}
          </span>
        </div>
      )}

      {scene.status === "generating" && (
        <div
          className="absolute inset-0"
          style={{
            background:
              "linear-gradient(90deg, var(--bg-surface) 25%, var(--bg-elevated) 50%, var(--bg-surface) 75%)",
            backgroundSize: "200% 100%",
            animation: "shimmer 1.5s ease-in-out infinite",
          }}
        >
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-[10px] text-accent-amber font-display animate-pulse">
              {size === "compact" ? "..." : "Generating..."}
            </span>
          </div>
        </div>
      )}

      {scene.status === "ready" && scene.imageUrl && (
        <>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={scene.imageUrl}
            alt={scene.title}
            className="absolute inset-0 w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
          <div className="absolute bottom-0 left-0 right-0 p-1.5">
            <p className="text-[10px] font-display text-white/90 truncate">
              {size === "compact" ? `${scene.index + 1}` : scene.title}
            </p>
          </div>

          {scene.videoUrl && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="h-6 w-6 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
                <svg
                  className="h-3 w-3 text-white ml-0.5"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M8 5v14l11-7z" />
                </svg>
              </div>
            </div>
          )}
        </>
      )}
    </motion.button>
  );
}
