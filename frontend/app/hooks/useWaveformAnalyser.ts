"use client";

import { useEffect, useRef } from "react";

export function useWaveformAnalyser(
  analyserNode: AnalyserNode | null,
  canvasRef: React.RefObject<HTMLCanvasElement | null>,
  options: {
    color?: string;
    lineWidth?: number;
    circular?: boolean;
    radius?: number;
  } = {},
): void {
  const rafRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !analyserNode) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const {
      color = "#d97757",
      lineWidth = 2,
      circular = false,
      radius = 60,
    } = options;

    const bufferLength = analyserNode.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    function draw() {
      rafRef.current = requestAnimationFrame(draw);
      analyserNode!.getByteFrequencyData(dataArray);

      const w = canvas!.width;
      const h = canvas!.height;
      ctx!.clearRect(0, 0, w, h);

      ctx!.strokeStyle = color;
      ctx!.lineWidth = lineWidth;
      ctx!.beginPath();

      if (circular) {
        const cx = w / 2;
        const cy = h / 2;
        const step = (Math.PI * 2) / bufferLength;

        for (let i = 0; i < bufferLength; i++) {
          const amplitude = dataArray[i] / 255;
          const r = radius + amplitude * 20;
          const angle = i * step - Math.PI / 2;
          const x = cx + Math.cos(angle) * r;
          const y = cy + Math.sin(angle) * r;
          if (i === 0) ctx!.moveTo(x, y);
          else ctx!.lineTo(x, y);
        }
        ctx!.closePath();
      } else {
        const sliceWidth = w / bufferLength;
        let x = 0;
        for (let i = 0; i < bufferLength; i++) {
          const v = dataArray[i] / 255;
          const y = h - v * h;
          if (i === 0) ctx!.moveTo(x, y);
          else ctx!.lineTo(x, y);
          x += sliceWidth;
        }
      }

      ctx!.stroke();
    }

    draw();

    return () => cancelAnimationFrame(rafRef.current);
  }, [
    analyserNode,
    canvasRef,
    options.color,
    options.lineWidth,
    options.circular,
    options.radius,
  ]);
}
