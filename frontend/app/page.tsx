"use client";

import { useEffect } from "react";
import { useConversationStore } from "./stores/conversationStore";
import { MOCK_AGENT_RESPONSES } from "./lib/mockData";
import { AgentPanel } from "./components/AgentPanel";
import { Workspace } from "./components/Workspace";
import { PlayerOverlay } from "./components/PlayerOverlay";

export default function Home() {
  const messages = useConversationStore((s) => s.messages);
  const startAgentMessage = useConversationStore((s) => s.startAgentMessage);
  const appendAgentChunk = useConversationStore((s) => s.appendAgentChunk);
  const finalizeAgentMessage = useConversationStore(
    (s) => s.finalizeAgentMessage
  );

  // Show welcome message on mount
  useEffect(() => {
    if (messages.length > 0) return;

    let cancelled = false;
    const text = MOCK_AGENT_RESPONSES.welcome;

    async function showWelcome() {
      const id = startAgentMessage();
      for (const char of text) {
        if (cancelled) break;
        appendAgentChunk(id, char);
        await new Promise((r) => setTimeout(r, 25));
      }
      if (!cancelled) finalizeAgentMessage(id);
    }

    showWelcome();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex h-full">
      <AgentPanel />
      <Workspace />
      <PlayerOverlay />
    </div>
  );
}
