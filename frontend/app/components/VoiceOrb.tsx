"use client";

import { useCallback } from "react";
import { motion } from "framer-motion";
import clsx from "clsx";
import { useUIStore } from "../stores/uiStore";
import { useStorybookStore } from "../stores/storybookStore";
import { useAudioRecorder } from "../hooks/useAudioRecorder";
import { useAgent } from "../hooks/useAgent";
import { useEditorContext } from "../lib/editorContext";
import { VoiceWaveform } from "./VoiceWaveform";

interface VoiceOrbProps {
  readonly compact?: boolean;
}

const stateStyles = {
  idle: "animate-[orb-pulse_3s_ease-in-out_infinite] bg-gradient-to-br from-accent-cyan/20 to-accent-cyan/5",
  listening:
    "animate-[orb-recording_1.5s_ease-in-out_infinite] bg-gradient-to-br from-accent-red/30 to-accent-red/10",
  thinking: "bg-gradient-to-br from-accent-amber/20 to-accent-amber/5",
  speaking:
    "animate-[orb-speaking_2s_ease-in-out_infinite] bg-gradient-to-br from-accent-green/20 to-accent-green/5",
} as const;

const stateLabels = {
  idle: "Tap to speak",
  listening: "Listening...",
  thinking: "Thinking...",
  speaking: "Speaking...",
} as const;

const stateBorderColors = {
  idle: "border-accent-cyan/30",
  listening: "border-accent-red/40",
  thinking: "border-accent-amber/30",
  speaking: "border-accent-green/30",
} as const;

export function VoiceOrb({ compact = false }: VoiceOrbProps) {
  const orbSize = compact ? 80 : 120;
  const iconSize = compact ? "h-5 w-5" : "h-8 w-8";

  const agentState = useUIStore((s) => s.agentState);
  const isRecording = useUIStore((s) => s.isRecording);
  const setRecording = useUIStore((s) => s.setRecording);
  const setAgentState = useUIStore((s) => s.setAgentState);
  const { startRecording, stopRecording, analyserNode, error } =
    useAudioRecorder();
  const { storybookId } = useEditorContext();
  const projectMode = useStorybookStore((s) => s.mode);
  const projectCharacters = useStorybookStore((s) => s.characters);
  const { sendAudio } = useAgent(storybookId, projectMode, projectCharacters);

  const handleClick = useCallback(async () => {
    if (agentState === "thinking" || agentState === "speaking") return;

    if (!isRecording) {
      console.debug(
        "[SayCut] VoiceOrb click: start recording, agentState:",
        agentState,
      );
      await startRecording();
      setRecording(true);
      setAgentState("listening");
    } else {
      console.debug("[SayCut] VoiceOrb click: stop recording");
      const base64Wav = stopRecording();
      setRecording(false);
      if (base64Wav) {
        sendAudio(base64Wav);
      }
    }
  }, [
    agentState,
    isRecording,
    startRecording,
    stopRecording,
    setRecording,
    setAgentState,
    sendAudio,
  ]);

  return (
    <div
      className={clsx(
        "flex flex-col items-center gap-2",
        compact ? "py-3" : "pb-8 pt-4",
      )}
    >
      <div
        className="relative flex items-center justify-center"
        style={{ width: orbSize, height: orbSize }}
      >
        {isRecording && (
          <VoiceWaveform
            analyserNode={analyserNode}
            size={orbSize + (compact ? 24 : 40)}
            color="var(--accent-red)"
          />
        )}

        {agentState === "thinking" && (
          <motion.div
            className="absolute inset-[-4px] rounded-full border-2 border-transparent border-t-accent-amber"
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
          />
        )}

        <motion.button
          className={clsx(
            "relative z-10 flex items-center justify-center rounded-full border-2 backdrop-blur-sm transition-colors",
            stateStyles[agentState],
            stateBorderColors[agentState],
            (agentState === "thinking" || agentState === "speaking") &&
              "cursor-not-allowed opacity-80",
          )}
          style={{ width: orbSize, height: orbSize }}
          whileTap={
            agentState === "idle" || agentState === "listening"
              ? { scale: 0.95 }
              : undefined
          }
          onClick={handleClick}
          aria-label={stateLabels[agentState]}
        >
          <svg
            className={clsx(
              iconSize,
              "transition-colors",
              agentState === "idle" && "text-accent-cyan",
              agentState === "listening" && "text-accent-red",
              agentState === "thinking" && "text-accent-amber",
              agentState === "speaking" && "text-accent-green",
            )}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
            <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
            <line x1="12" y1="19" x2="12" y2="22" />
          </svg>
        </motion.button>
      </div>

      <span
        className={clsx(
          "font-display text-text-muted select-none",
          compact ? "text-[10px]" : "text-xs",
        )}
      >
        {stateLabels[agentState]}
      </span>

      {error && (
        <p className="text-xs text-accent-red max-w-xs text-center">{error}</p>
      )}
    </div>
  );
}
