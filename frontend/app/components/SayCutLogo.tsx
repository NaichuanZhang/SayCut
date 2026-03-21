"use client";

import clsx from "clsx";

type LogoSize = "sm" | "md" | "lg" | "xl";
type LogoVariant = "full" | "mark" | "wordmark";

interface SayCutLogoProps {
  size?: LogoSize;
  variant?: LogoVariant;
  className?: string;
}

const sizeMap: Record<LogoSize, number> = {
  sm: 24,
  md: 32,
  lg: 48,
  xl: 80,
};

const fontSizeMap: Record<LogoSize, string> = {
  sm: "text-xs",
  md: "text-sm",
  lg: "text-xl",
  xl: "text-3xl",
};

function LogoMark({ size }: { size: number }) {
  // 3 bars: left full, center with diagonal cut, right slightly shorter
  // Viewbox 40x48 — bars are 8px wide with 4px gaps
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="logo-mark"
    >
      {/* Bar 1 — left, full height */}
      <rect x="0" y="0" width="8" height="48" rx="1.5" fill="currentColor" />

      {/* Bar 2 — center, diagonal cut through middle */}
      <clipPath id="cut-clip">
        {/* Top portion: above the diagonal */}
        <polygon points="16,0 24,0 24,18 16,26" />
        {/* Bottom portion: below the diagonal */}
        <polygon points="16,30 24,22 24,48 16,48" />
      </clipPath>
      <rect
        x="16"
        y="0"
        width="8"
        height="48"
        rx="1.5"
        fill="currentColor"
        clipPath="url(#cut-clip)"
      />

      {/* Bar 3 — right, slightly shorter */}
      <rect x="32" y="4" width="8" height="40" rx="1.5" fill="currentColor" />
    </svg>
  );
}

function Wordmark({ sizeKey }: { sizeKey: LogoSize }) {
  return (
    <span className={clsx("font-display leading-none select-none", fontSizeMap[sizeKey])}>
      <span className="font-normal text-text-primary">Say</span>
      <span
        className="font-bold text-text-primary"
        style={{
          clipPath: "polygon(0 0, 100% 0, 100% 100%, 0 100%)",
        }}
      >
        Cut
      </span>
    </span>
  );
}

export function SayCutLogo({
  size = "md",
  variant = "full",
  className,
}: SayCutLogoProps) {
  const px = sizeMap[size];

  return (
    <span
      className={clsx(
        "inline-flex items-center gap-2 text-accent-cyan logo-glow",
        className,
      )}
    >
      {(variant === "full" || variant === "mark") && <LogoMark size={px} />}
      {(variant === "full" || variant === "wordmark") && (
        <Wordmark sizeKey={size} />
      )}
    </span>
  );
}
