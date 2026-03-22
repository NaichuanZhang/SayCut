"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { useConversationStore } from "../../stores/conversationStore";
import { useStorybookStore } from "../../stores/storybookStore";
import { useUIStore } from "../../stores/uiStore";
import { MOCK_AGENT_RESPONSES } from "../../lib/mockData";
import { fetchStorybook, fetchMessages } from "../../lib/api";
import { AgentPanel } from "../../components/AgentPanel";
import { Workspace } from "../../components/Workspace";
import { PlayerOverlay } from "../../components/PlayerOverlay";
import { CharacterConfig, Message, Scene, StoryMode } from "../../lib/types";
import { stripToolCalls } from "../../lib/stripToolCalls";
import { EditorContext } from "../../lib/editorContext";
import { ModeSelector } from "../../components/ModeSelector";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:3001";

function prefixAssetUrl(url: string | null): string | null {
  if (!url) return null;
  if (url.startsWith("http")) return url;
  return `${BACKEND_URL}${url}`;
}

export default function EditorPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const isNew = id === "new";
  const [ready, setReady] = useState(isNew);
  const [modeSelected, setModeSelected] = useState(!isNew);
  const hydrated = useRef(false);

  const messages = useConversationStore((s) => s.messages);
  const loadMessages = useConversationStore((s) => s.loadMessages);
  const startAgentMessage = useConversationStore((s) => s.startAgentMessage);
  const appendAgentChunk = useConversationStore((s) => s.appendAgentChunk);
  const finalizeAgentMessage = useConversationStore(
    (s) => s.finalizeAgentMessage,
  );

  const setStorybookId = useStorybookStore((s) => s.setStorybookId);
  const setMode = useStorybookStore((s) => s.setMode);
  const setCharacters = useStorybookStore((s) => s.setCharacters);
  const loadScenes = useStorybookStore((s) => s.loadScenes);
  const selectScene = useUIStore((s) => s.selectScene);

  const mode = useStorybookStore((s) => s.mode);
  const characters = useStorybookStore((s) => s.characters);

  // Clean up stores on unmount
  useEffect(() => {
    return () => {
      useStorybookStore.getState().clear();
      useConversationStore.getState().clear();
      useUIStore.getState().selectScene(null);
    };
  }, []);

  // Hydrate store from backend for existing storybooks
  useEffect(() => {
    if (isNew || hydrated.current) return;
    hydrated.current = true;

    Promise.all([fetchStorybook(id), fetchMessages(id)])
      .then(([data, rawMsgs]) => {
        setStorybookId(data.id);
        if (data.mode) setMode(data.mode);
        if (data.characters) setCharacters(data.characters);
        const scenes: Scene[] = data.scenes.map((s) => ({
          ...s,
          imageUrl: prefixAssetUrl(s.imageUrl),
          videoUrl: prefixAssetUrl(s.videoUrl),
          audioUrl: prefixAssetUrl(s.audioUrl),
        }));
        loadScenes(scenes);
        if (scenes.length > 0) {
          selectScene(scenes[0].id);
        }

        // Restore conversation history, filtering out internal messages
        const restored: Message[] = rawMsgs
          .filter((m) => {
            if (m.text.startsWith("<tool_response>")) return false;
            if (m.text === "[audio input]") return false;
            if (m.text.startsWith("Continue —")) return false;
            return true;
          })
          .map((m) => ({
            id: m.id,
            role:
              m.role === "assistant" ? ("agent" as const) : ("user" as const),
            text: m.role === "assistant" ? stripToolCalls(m.text) : m.text,
            timestamp: new Date(m.createdAt).getTime(),
          }))
          .filter((m) => m.text.length > 0);

        if (restored.length > 0) {
          loadMessages(restored);
        }

        setReady(true);
      })
      .catch((err) => {
        console.error("Failed to load storybook:", err);
        setReady(true);
      });
  }, [
    id,
    isNew,
    setStorybookId,
    setMode,
    setCharacters,
    loadScenes,
    loadMessages,
    selectScene,
  ]);

  // Show welcome message on mount (only for new projects after mode selection)
  useEffect(() => {
    if (!isNew || !modeSelected || messages.length > 0) return;

    let cancelled = false;
    const text = MOCK_AGENT_RESPONSES.welcome;

    async function showWelcome() {
      const msgId = startAgentMessage();
      for (const char of text) {
        if (cancelled) break;
        appendAgentChunk(msgId, char);
        await new Promise((r) => setTimeout(r, 25));
      }
      if (!cancelled) finalizeAgentMessage(msgId);
    }

    showWelcome();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isNew, modeSelected]);

  const handleModeConfirm = (
    selectedMode: StoryMode,
    selectedCharacters: readonly CharacterConfig[],
  ) => {
    setMode(selectedMode);
    if (selectedMode === "movie") {
      setCharacters(selectedCharacters);
    }
    setModeSelected(true);
  };

  const editorCtx = useMemo(
    () => ({ storybookId: isNew ? undefined : id }),
    [isNew, id],
  );

  if (!ready) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="h-6 w-6 rounded-full border-2 border-accent-cyan border-t-transparent animate-spin" />
      </div>
    );
  }

  // Show mode selection screen for new projects
  if (isNew && !modeSelected) {
    return <ModeSelector onConfirm={handleModeConfirm} />;
  }

  return (
    <EditorContext.Provider value={editorCtx}>
      <div className="flex h-full">
        <AgentPanel />
        <Workspace />
        <PlayerOverlay />
      </div>
    </EditorContext.Provider>
  );
}
