"use client";

import { useCallback, useRef } from "react";
import { useConversationStore } from "../stores/conversationStore";
import { useStorybookStore } from "../stores/storybookStore";
import { useUIStore } from "../stores/uiStore";
import { handleMockInteraction, MockAgentCallbacks } from "../lib/mockAgent";

export function useMockAgent() {
  const isProcessing = useRef(false);
  const firstSceneAdded = useRef(false);

  const addUserMessage = useConversationStore((s) => s.addUserMessage);
  const startAgentMessage = useConversationStore((s) => s.startAgentMessage);
  const appendAgentChunk = useConversationStore((s) => s.appendAgentChunk);
  const finalizeAgentMessage = useConversationStore(
    (s) => s.finalizeAgentMessage
  );
  const addToolStatus = useConversationStore((s) => s.addToolStatus);

  const addScene = useStorybookStore((s) => s.addScene);
  const updateSceneImage = useStorybookStore((s) => s.updateSceneImage);
  const updateSceneStatus = useStorybookStore((s) => s.updateSceneStatus);

  const setAgentState = useUIStore((s) => s.setAgentState);
  const selectScene = useUIStore((s) => s.selectScene);

  const sendMessage = useCallback(async () => {
    if (isProcessing.current) return;
    isProcessing.current = true;
    firstSceneAdded.current = false;

    addUserMessage();

    const callbacks: MockAgentCallbacks = {
      onThinking: () => setAgentState("thinking"),
      onStreamStart: () => startAgentMessage(),
      onStreamChunk: (id, char) => appendAgentChunk(id, char),
      onStreamEnd: (id) => finalizeAgentMessage(id),
      onToolStatus: (name, status) => addToolStatus(name, status),
      onSceneAdd: (scene) => {
        addScene(scene);
        // Auto-select the first scene in the workspace
        if (!firstSceneAdded.current) {
          firstSceneAdded.current = true;
          selectScene(scene.id);
        }
      },
      onSceneStatusUpdate: (sceneId, status) =>
        updateSceneStatus(sceneId, status),
      onSceneImageReady: (sceneId, imageUrl) =>
        updateSceneImage(sceneId, imageUrl),
      onSpeaking: () => setAgentState("speaking"),
      onIdle: () => setAgentState("idle"),
    };

    try {
      await handleMockInteraction(callbacks);
    } finally {
      isProcessing.current = false;
    }
  }, [
    addUserMessage,
    startAgentMessage,
    appendAgentChunk,
    finalizeAgentMessage,
    addToolStatus,
    addScene,
    updateSceneImage,
    updateSceneStatus,
    setAgentState,
    selectScene,
  ]);

  return { sendMessage };
}
