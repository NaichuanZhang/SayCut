"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { useConversationStore } from "../../stores/conversationStore";
import { useStorybookStore } from "../../stores/storybookStore";
import { useUIStore } from "../../stores/uiStore";
import { MOCK_AGENT_RESPONSES } from "../../lib/mockData";
import { fetchStorybook } from "../../lib/api";
import { AgentPanel } from "../../components/AgentPanel";
import { Workspace } from "../../components/Workspace";
import { PlayerOverlay } from "../../components/PlayerOverlay";
import { Scene } from "../../lib/types";
import { EditorContext } from "../../lib/editorContext";

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
  const hydrated = useRef(false);

  const messages = useConversationStore((s) => s.messages);
  const startAgentMessage = useConversationStore((s) => s.startAgentMessage);
  const appendAgentChunk = useConversationStore((s) => s.appendAgentChunk);
  const finalizeAgentMessage = useConversationStore(
    (s) => s.finalizeAgentMessage,
  );

  const setStorybookId = useStorybookStore((s) => s.setStorybookId);
  const loadScenes = useStorybookStore((s) => s.loadScenes);
  const selectScene = useUIStore((s) => s.selectScene);

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

    fetchStorybook(id)
      .then((data) => {
        setStorybookId(data.id);
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
        setReady(true);
      })
      .catch((err) => {
        console.error("Failed to load storybook:", err);
        setReady(true);
      });
  }, [id, isNew, setStorybookId, loadScenes, selectScene]);

  // Show welcome message on mount (only for new projects)
  useEffect(() => {
    if (!isNew || messages.length > 0) return;

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
  }, [isNew]);

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
