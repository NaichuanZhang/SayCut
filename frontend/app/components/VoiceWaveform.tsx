"use client";

import { useRef } from "react";
import { useWaveformAnalyser } from "../hooks/useWaveformAnalyser";

interface VoiceWaveformProps {
  readonly analyserNode: AnalyserNode | null;
  readonly size?: number;
  readonly color?: string;
}

export function VoiceWaveform({
  analyserNode,
  size = 160,
  color = "#c95d4f",
}: VoiceWaveformProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useWaveformAnalyser(analyserNode, canvasRef, {
    color,
    lineWidth: 2,
    circular: true,
    radius: size / 2 - 20,
  });

  return (
    <canvas
      ref={canvasRef}
      width={size}
      height={size}
      className="absolute inset-0 pointer-events-none"
      style={{ width: size, height: size }}
    />
  );
}
