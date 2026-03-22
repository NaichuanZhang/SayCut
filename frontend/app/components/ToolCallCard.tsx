"use client";

import { motion } from "framer-motion";
import clsx from "clsx";
import { Message } from "../lib/types";

interface ToolCallCardProps {
  readonly message: Message;
}

const TOOL_ICONS: Record<string, string> = {
  generate_script: "doc",
  generate_scene_image: "image",
};

function ToolIcon({ toolName }: { toolName: string }) {
  const type = TOOL_ICONS[toolName] ?? "default";

  if (type === "doc") {
    return (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
      </svg>
    );
  }

  if (type === "image") {
    return (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
        <circle cx="8.5" cy="8.5" r="1.5" />
        <polyline points="21 15 16 10 5 21" />
      </svg>
    );
  }

  return (
    <svg
      className="h-4 w-4"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
    </svg>
  );
}

export function ToolCallCard({ message }: ToolCallCardProps) {
  const toolName = message.toolName ?? "tool";
  const isComplete =
    message.toolStatus === "done" ||
    message.toolStatus?.includes("ready") ||
    message.toolStatus?.includes("Ready");
  const isImageResult = isComplete && toolName.includes("image");

  return (
    <motion.div
      className={clsx(
        "rounded-lg bg-bg-elevated border border-border-subtle overflow-hidden",
        "border-l-[3px]",
        isComplete ? "border-l-accent-green" : "border-l-accent-amber",
      )}
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="px-3 py-2.5 flex items-start gap-2.5">
        {/* Icon */}
        <div
          className={clsx(
            "mt-0.5 flex-shrink-0",
            isComplete ? "text-accent-green" : "text-accent-amber",
          )}
        >
          {isComplete ? (
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none">
              <path
                d="M20 6L9 17l-5-5"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          ) : (
            <ToolIcon toolName={toolName} />
          )}
        </div>

        <div className="flex-1 min-w-0">
          {/* Tool name */}
          <p className="font-display text-[11px] text-text-muted truncate">
            {toolName}
          </p>
          {/* Status text */}
          <p
            className={clsx(
              "text-xs mt-0.5",
              isComplete ? "text-text-primary" : "text-accent-amber",
            )}
          >
            {message.text}
          </p>

          {/* Progress bar for generating */}
          {!isComplete && (
            <div className="mt-2 h-1 w-full rounded-full bg-bg-surface overflow-hidden">
              <div
                className="h-full rounded-full bg-accent-amber/60"
                style={{
                  animation: "progress-bar 2s ease-in-out infinite",
                }}
              />
            </div>
          )}

          {/* Thumbnail for image results */}
          {isImageResult && (
            <div className="mt-2 w-16 h-9 rounded bg-bg-surface overflow-hidden">
              <div
                className="w-full h-full"
                style={{
                  background:
                    "linear-gradient(135deg, var(--accent-green) 0%, var(--accent-cyan) 100%)",
                  opacity: 0.3,
                }}
              />
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
