"use client";

import { useState, useRef } from "react";
import clsx from "clsx";
import { motion } from "framer-motion";
import { CharacterConfig, StoryMode } from "../lib/types";
import { SayCutLogo } from "./SayCutLogo";

const AVAILABLE_VOICES = [
  { id: "Linda", label: "Linda" },
  { id: "Jack", label: "Jack" },
] as const;

const VOICE_SAMPLE_URL: Record<string, string> = {
  Linda: "/voice-samples/linda.wav",
  Jack: "/voice-samples/jack.wav",
};

interface ModeSelectorProps {
  readonly onConfirm: (
    mode: StoryMode,
    characters: readonly CharacterConfig[],
  ) => void;
}

export function ModeSelector({ onConfirm }: ModeSelectorProps) {
  const [selectedMode, setSelectedMode] = useState<StoryMode | null>(null);
  const [char1Name, setChar1Name] = useState("Linda");
  const [char1Voice, setChar1Voice] = useState("Linda");
  const [char2Name, setChar2Name] = useState("Jack");
  const [char2Voice, setChar2Voice] = useState("Jack");
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playingVoice, setPlayingVoice] = useState<string | null>(null);

  const handlePlaySample = (voiceId: string) => {
    const url = VOICE_SAMPLE_URL[voiceId];
    if (!url || !audioRef.current) return;

    if (playingVoice === voiceId) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setPlayingVoice(null);
      return;
    }

    audioRef.current.src = url;
    audioRef.current.play().catch(() => {});
    setPlayingVoice(voiceId);
  };

  const handleConfirm = () => {
    if (!selectedMode) return;
    if (selectedMode === "story") {
      onConfirm("story", []);
      return;
    }
    const characters: CharacterConfig[] = [
      { name: "Narrator", voice: "Linda" },
      { name: char1Name || "Linda", voice: char1Voice },
      { name: char2Name || "Jack", voice: char2Voice },
    ];
    onConfirm("movie", characters);
  };

  return (
    <div className="flex h-full items-center justify-center">
      <audio
        ref={audioRef}
        onEnded={() => setPlayingVoice(null)}
        className="hidden"
      />

      <motion.div
        className="max-w-2xl w-full px-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div className="text-center mb-10">
          <div className="mx-auto mb-4 opacity-30">
            <SayCutLogo size="lg" variant="mark" />
          </div>
          <h1 className="font-display text-2xl text-text-primary mb-2">
            What are you creating?
          </h1>
          <p className="text-sm text-text-muted">
            Choose a mode to get started
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-8">
          {/* Story mode card */}
          <button
            onClick={() => setSelectedMode("story")}
            className={clsx(
              "group rounded-xl border p-6 text-left transition-all",
              selectedMode === "story"
                ? "border-accent-cyan bg-accent-cyan/5"
                : "border-border-subtle bg-bg-surface/60 hover:border-accent-cyan/30",
            )}
          >
            <div className="text-3xl mb-3 opacity-60">
              <svg
                className="h-8 w-8"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <path d="M4 19.5A2.5 2.5 0 016.5 17H20" />
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" />
              </svg>
            </div>
            <h3 className="font-display text-lg text-text-primary mb-1">
              Story
            </h3>
            <p className="text-xs text-text-muted leading-relaxed">
              Single narrator. Classic storybook style with narration text per
              scene.
            </p>
          </button>

          {/* Movie mode card */}
          <button
            onClick={() => setSelectedMode("movie")}
            className={clsx(
              "group rounded-xl border p-6 text-left transition-all",
              selectedMode === "movie"
                ? "border-accent-amber bg-accent-amber/5"
                : "border-border-subtle bg-bg-surface/60 hover:border-accent-amber/30",
            )}
          >
            <div className="text-3xl mb-3 opacity-60">
              <svg
                className="h-8 w-8"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <rect x="2" y="2" width="20" height="20" rx="2.18" />
                <line x1="7" y1="2" x2="7" y2="22" />
                <line x1="17" y1="2" x2="17" y2="22" />
                <line x1="2" y1="12" x2="22" y2="12" />
                <line x1="2" y1="7" x2="7" y2="7" />
                <line x1="2" y1="17" x2="7" y2="17" />
                <line x1="17" y1="7" x2="22" y2="7" />
                <line x1="17" y1="17" x2="22" y2="17" />
              </svg>
            </div>
            <h3 className="font-display text-lg text-text-primary mb-1">
              Movie
            </h3>
            <p className="text-xs text-text-muted leading-relaxed">
              2-person dialogue with a narrator. Multiple voices bring
              characters to life.
            </p>
          </button>
        </div>

        {/* Movie character config */}
        {selectedMode === "movie" && (
          <motion.div
            className="rounded-xl border border-border-subtle bg-bg-surface/60 p-6 mb-8 space-y-4"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            transition={{ duration: 0.3 }}
          >
            <h3 className="font-display text-sm text-text-muted uppercase tracking-wider">
              Characters
            </h3>

            {/* Character 1 */}
            <div className="flex items-center gap-3">
              <input
                type="text"
                value={char1Name}
                onChange={(e) => setChar1Name(e.target.value)}
                placeholder="Character 1 name"
                className="flex-1 rounded-lg bg-bg-elevated border border-border-subtle px-3 py-2 text-sm text-text-primary placeholder:text-text-muted/40 focus:outline-none focus:ring-1 focus:ring-accent-cyan/50"
              />
              <select
                value={char1Voice}
                onChange={(e) => setChar1Voice(e.target.value)}
                className="rounded-lg bg-bg-elevated border border-border-subtle px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-1 focus:ring-accent-cyan/50"
              >
                {AVAILABLE_VOICES.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.label}
                  </option>
                ))}
              </select>
              <button
                onClick={() => handlePlaySample(char1Voice)}
                className={clsx(
                  "h-8 w-8 rounded-full flex items-center justify-center flex-shrink-0 transition-colors",
                  playingVoice === char1Voice
                    ? "bg-accent-cyan/20 text-accent-cyan"
                    : "bg-bg-elevated text-text-muted hover:text-text-primary",
                )}
                aria-label="Preview voice"
              >
                {playingVoice === char1Voice ? (
                  <svg
                    className="h-4 w-4"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                  >
                    <rect x="6" y="4" width="4" height="16" rx="1" />
                    <rect x="14" y="4" width="4" height="16" rx="1" />
                  </svg>
                ) : (
                  <svg
                    className="h-4 w-4 ml-0.5"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                  >
                    <path d="M8 5v14l11-7z" />
                  </svg>
                )}
              </button>
            </div>

            {/* Character 2 */}
            <div className="flex items-center gap-3">
              <input
                type="text"
                value={char2Name}
                onChange={(e) => setChar2Name(e.target.value)}
                placeholder="Character 2 name"
                className="flex-1 rounded-lg bg-bg-elevated border border-border-subtle px-3 py-2 text-sm text-text-primary placeholder:text-text-muted/40 focus:outline-none focus:ring-1 focus:ring-accent-cyan/50"
              />
              <select
                value={char2Voice}
                onChange={(e) => setChar2Voice(e.target.value)}
                className="rounded-lg bg-bg-elevated border border-border-subtle px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-1 focus:ring-accent-cyan/50"
              >
                {AVAILABLE_VOICES.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.label}
                  </option>
                ))}
              </select>
              <button
                onClick={() => handlePlaySample(char2Voice)}
                className={clsx(
                  "h-8 w-8 rounded-full flex items-center justify-center flex-shrink-0 transition-colors",
                  playingVoice === char2Voice
                    ? "bg-accent-cyan/20 text-accent-cyan"
                    : "bg-bg-elevated text-text-muted hover:text-text-primary",
                )}
                aria-label="Preview voice"
              >
                {playingVoice === char2Voice ? (
                  <svg
                    className="h-4 w-4"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                  >
                    <rect x="6" y="4" width="4" height="16" rx="1" />
                    <rect x="14" y="4" width="4" height="16" rx="1" />
                  </svg>
                ) : (
                  <svg
                    className="h-4 w-4 ml-0.5"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                  >
                    <path d="M8 5v14l11-7z" />
                  </svg>
                )}
              </button>
            </div>

            <p className="text-[11px] text-text-muted/60">
              A Narrator voice (Linda) is included automatically.
            </p>
          </motion.div>
        )}

        {/* Confirm button */}
        <div className="flex justify-center">
          <button
            onClick={handleConfirm}
            disabled={!selectedMode}
            className={clsx(
              "px-8 py-3 rounded-xl font-display text-sm transition-all",
              selectedMode
                ? "bg-accent-cyan text-black hover:bg-accent-cyan/90"
                : "bg-bg-elevated text-text-muted/30 cursor-not-allowed",
            )}
          >
            Start Creating
          </button>
        </div>
      </motion.div>
    </div>
  );
}
