"use client";

import clsx from "clsx";

interface StatusPillProps {
  readonly text: string;
  readonly variant?: "generating" | "complete";
}

export function StatusPill({ text, variant = "generating" }: StatusPillProps) {
  return (
    <div
      className={clsx(
        "inline-flex items-center gap-2 rounded-full px-3 py-1.5 font-display text-xs",
        variant === "generating" &&
          "bg-accent-amber/10 text-accent-amber animate-[status-pulse_2s_ease-in-out_infinite]",
        variant === "complete" && "bg-accent-green/10 text-accent-green"
      )}
    >
      {variant === "generating" && (
        <span className="h-1.5 w-1.5 rounded-full bg-accent-amber animate-pulse" />
      )}
      {variant === "complete" && (
        <svg className="h-3 w-3" viewBox="0 0 12 12" fill="none">
          <path
            d="M2 6l3 3 5-5"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      )}
      {text}
    </div>
  );
}
