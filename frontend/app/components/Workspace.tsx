"use client";

import { useUIStore } from "../stores/uiStore";
import { SceneStrip } from "./SceneStrip";
import { SceneEditor } from "./SceneEditor";
import { SayCutLogo } from "./SayCutLogo";

export function Workspace() {
  const toggleAgentPanel = useUIStore((s) => s.toggleAgentPanel);

  return (
    <div className="flex-1 flex flex-col h-full min-w-0">
      {/* Mobile agent panel toggle */}
      <div className="flex items-center px-4 py-2 border-b border-border-subtle md:hidden">
        <button
          onClick={toggleAgentPanel}
          className="flex items-center gap-2 text-text-muted hover:text-text-primary transition-colors"
          aria-label="Toggle agent panel"
        >
          <svg
            className="h-5 w-5"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          >
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
          <SayCutLogo size="sm" variant="mark" className="ml-1" />
          <span className="font-display text-xs">SayCut</span>
        </button>
      </div>

      <SceneStrip />
      <SceneEditor />
    </div>
  );
}
