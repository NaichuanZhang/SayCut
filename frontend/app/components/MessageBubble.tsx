"use client";

import clsx from "clsx";
import { Message } from "../lib/types";

interface MessageBubbleProps {
  readonly message: Message;
  readonly compact?: boolean;
}

export function MessageBubble({ message, compact = false }: MessageBubbleProps) {
  if (message.role === "user") {
    return (
      <div className="flex items-center gap-2 self-end">
        <span
          className={clsx(
            "text-text-muted font-display",
            compact ? "text-[10px]" : "text-xs"
          )}
        >
          You
        </span>
        <div
          className={clsx(
            "flex items-center gap-1.5 rounded-full bg-accent-cyan/10",
            compact ? "px-3 py-1.5" : "px-4 py-2"
          )}
        >
          <svg
            className={clsx(
              "text-accent-cyan",
              compact ? "h-3 w-10" : "h-4 w-16"
            )}
            viewBox="0 0 64 16"
            fill="none"
          >
            {[4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60].map(
              (x, i) => {
                const h = [3, 6, 10, 14, 8, 12, 6, 14, 10, 7, 12, 5, 9, 6, 3][i];
                return (
                  <rect
                    key={x}
                    x={x - 1}
                    y={8 - h / 2}
                    width="2"
                    height={h}
                    rx="1"
                    fill="currentColor"
                  />
                );
              }
            )}
          </svg>
        </div>
      </div>
    );
  }

  if (message.role === "tool") {
    return null; // Tool messages are handled by ToolCallCard in the new layout
  }

  // Agent message
  return (
    <div className="self-start">
      <div
        className={clsx(
          "rounded-2xl rounded-tl-sm bg-bg-surface border border-border-subtle",
          compact ? "px-3 py-2" : "px-4 py-3"
        )}
      >
        <p
          className={clsx(
            "leading-relaxed text-text-primary",
            compact ? "text-xs" : "text-sm"
          )}
        >
          {message.text}
          {message.isStreaming && (
            <span className="inline-block w-0.5 h-4 bg-accent-cyan ml-0.5 animate-pulse align-text-bottom" />
          )}
        </p>
      </div>
    </div>
  );
}
