"use client";

import clsx from "clsx";
import Link from "next/link";
import { useUIStore } from "../stores/uiStore";
import { ActivityLog } from "./ActivityLog";
import { VoiceOrb } from "./VoiceOrb";
import { SayCutLogo } from "./SayCutLogo";

const stateColors = {
  idle: "bg-accent-cyan",
  listening: "bg-accent-red",
  thinking: "bg-accent-amber",
  speaking: "bg-accent-green",
} as const;

const stateText = {
  idle: "Idle",
  listening: "Listening",
  thinking: "Thinking",
  speaking: "Speaking",
} as const;

export function AgentPanel() {
  const agentState = useUIStore((s) => s.agentState);
  const isAgentPanelOpen = useUIStore((s) => s.isAgentPanelOpen);

  return (
    <>
      {/* Mobile backdrop */}
      {isAgentPanelOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 backdrop-blur-sm md:hidden"
          onClick={() => useUIStore.getState().toggleAgentPanel()}
        />
      )}

      <aside
        className={clsx(
          "flex flex-col h-full bg-bg-surface/80 backdrop-blur-sm border-r border-border-subtle",
          "w-80 flex-shrink-0",
          // Mobile: slide-in overlay
          "fixed z-40 md:relative md:z-auto",
          "transition-transform duration-300 ease-out",
          isAgentPanelOpen
            ? "translate-x-0"
            : "-translate-x-full md:translate-x-0 md:hidden",
        )}
      >
        {/* Header */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-border-subtle">
          <Link
            href="/"
            className="text-text-muted hover:text-text-primary transition-colors mr-1"
            title="Back to projects"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path
                d="M10 3L5 8L10 13"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </Link>
          <SayCutLogo size="sm" variant="full" />
          <span className="ml-auto flex items-center gap-1.5">
            <div
              className={clsx(
                "h-2 w-2 rounded-full transition-colors",
                stateColors[agentState],
                (agentState === "thinking" || agentState === "listening") &&
                  "animate-pulse",
              )}
            />
            <span className="font-display text-[10px] text-text-muted/60">
              {stateText[agentState]}
            </span>
          </span>
        </div>

        {/* Activity log */}
        <ActivityLog />

        {/* Voice orb */}
        <div className="border-t border-border-subtle">
          <VoiceOrb compact />
        </div>
      </aside>
    </>
  );
}
