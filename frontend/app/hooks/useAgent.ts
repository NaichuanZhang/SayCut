"use client";

import { useCallback, useEffect, useRef } from "react";
import { useConversationStore } from "../stores/conversationStore";
import { useStorybookStore } from "../stores/storybookStore";
import { useUIStore } from "../stores/uiStore";
import { WSClient, ServerMessage } from "../lib/wsClient";
import { DialogueLine, Scene, StoryMode, CharacterConfig } from "../lib/types";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:3001";

function prefixAssetUrl(url: string | null): string | null {
  if (!url) return null;
  if (url.startsWith("http")) return url;
  return `${BACKEND_URL}${url}`;
}

export function useAgent(
  storybookId?: string,
  projectMode?: StoryMode,
  projectCharacters?: readonly CharacterConfig[],
) {
  const clientRef = useRef<WSClient | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const isProcessing = useRef(false);
  const firstSceneAdded = useRef(false);

  const addUserMessage = useConversationStore((s) => s.addUserMessage);
  const startAgentMessage = useConversationStore((s) => s.startAgentMessage);
  const appendAgentChunk = useConversationStore((s) => s.appendAgentChunk);
  const finalizeAgentMessage = useConversationStore(
    (s) => s.finalizeAgentMessage,
  );
  const addToolStatus = useConversationStore((s) => s.addToolStatus);

  const setStorybookId = useStorybookStore((s) => s.setStorybookId);
  const addScene = useStorybookStore((s) => s.addScene);
  const updateSceneImage = useStorybookStore((s) => s.updateSceneImage);
  const updateSceneVideo = useStorybookStore((s) => s.updateSceneVideo);
  const updateSceneTTS = useStorybookStore((s) => s.updateSceneTTS);
  const updateSceneStatus = useStorybookStore((s) => s.updateSceneStatus);
  const updateSceneIndex = useStorybookStore((s) => s.updateSceneIndex);
  const removeScene = useStorybookStore((s) => s.removeScene);
  const clear = useStorybookStore((s) => s.clear);

  const setAgentState = useUIStore((s) => s.setAgentState);
  const selectScene = useUIStore((s) => s.selectScene);

  const handleMessage = useCallback(
    (msg: ServerMessage) => {
      console.debug("[SayCut] handleMessage:", msg.type);

      switch (msg.type) {
        case "session_created":
          sessionIdRef.current = msg.session_id as string;
          try {
            sessionStorage.setItem(
              `saycut-session-${storybookId ?? "new"}`,
              msg.session_id as string,
            );
          } catch {
            // sessionStorage may be unavailable in some contexts
          }
          console.debug("[SayCut] Session created:", sessionIdRef.current);
          // Send project mode if known (for new projects)
          if (projectMode && !storybookId) {
            clientRef.current?.sendSetProjectMode(
              projectMode,
              projectCharacters,
            );
          }
          // If resuming an existing storybook, tell the backend
          if (storybookId) {
            clientRef.current?.sendLoadStorybook(storybookId);
          }
          break;

        case "storybook_created":
          // Don't clear scenes if we're resuming — they were loaded from REST
          if (!storybookId) {
            clear();
          }
          setStorybookId(msg.storybook_id as string);
          firstSceneAdded.current = false;
          console.debug("[SayCut] Storybook created:", msg.storybook_id);
          break;

        case "agent_thinking":
          setAgentState("thinking");
          console.debug("[SayCut] agentState -> thinking");
          break;

        case "agent_stream_start": {
          const msgId = startAgentMessage();
          // Store message ID for subsequent chunks
          (
            clientRef.current as unknown as Record<string, string>
          ).__currentMsgId = msgId;
          setAgentState("speaking");
          console.debug("[SayCut] agentState -> speaking, msgId:", msgId);
          break;
        }

        case "agent_stream_chunk": {
          const currentId =
            (clientRef.current as unknown as Record<string, string>)
              ?.__currentMsgId ?? (msg.message_id as string);
          appendAgentChunk(currentId, msg.text as string);
          break;
        }

        case "agent_stream_end": {
          const endId =
            (clientRef.current as unknown as Record<string, string>)
              ?.__currentMsgId ?? (msg.message_id as string);
          finalizeAgentMessage(endId);
          // Fallback: reset state in case agent_idle is not received
          setAgentState("idle");
          isProcessing.current = false;
          console.debug(
            "[SayCut] agent_stream_end: agentState -> idle, isProcessing -> false",
          );
          break;
        }

        case "agent_idle":
          // Definitive signal from backend that agent is done
          setAgentState("idle");
          isProcessing.current = false;
          console.debug(
            "[SayCut] agent_idle: agentState -> idle, isProcessing -> false",
          );
          break;

        case "tool_status":
          addToolStatus(
            msg.tool_name as string,
            msg.status as string,
            msg.scene_id as string | undefined,
          );
          break;

        case "scene_add": {
          const sceneData = msg.scene as Record<string, unknown>;
          const scene: Scene = {
            id: sceneData.id as string,
            index: sceneData.index as number,
            title: sceneData.title as string,
            narrationText: (sceneData.narrationText as string) ?? "",
            visualDescription: (sceneData.visualDescription as string) ?? "",
            imageUrl: prefixAssetUrl(
              (sceneData.imageUrl as string | null) ?? null,
            ),
            videoUrl: prefixAssetUrl(
              (sceneData.videoUrl as string | null) ?? null,
            ),
            audioUrl: prefixAssetUrl(
              (sceneData.audioUrl as string | null) ?? null,
            ),
            dialogueLines:
              (sceneData.dialogueLines as DialogueLine[] | undefined) ??
              undefined,
            status: (sceneData.status as Scene["status"]) ?? "empty",
          };
          addScene(scene);
          // Auto-select first scene, or any scene if nothing is selected
          const currentSelected = useUIStore.getState().selectedSceneId;
          if (!firstSceneAdded.current || !currentSelected) {
            firstSceneAdded.current = true;
            selectScene(scene.id);
          }
          break;
        }

        case "scene_remove": {
          const removedId = msg.scene_id as string;
          removeScene(removedId);
          const selected = useUIStore.getState().selectedSceneId;
          if (selected === removedId) selectScene(null);
          break;
        }

        case "scene_update": {
          const sceneId = msg.scene_id as string;
          const field = msg.field as string;
          const value = msg.value as string;
          console.debug("[SayCut] scene_update:", { sceneId, field });

          if (field === "imageUrl") {
            updateSceneImage(sceneId, prefixAssetUrl(value) ?? value);
          } else if (field === "videoUrl") {
            updateSceneVideo(sceneId, prefixAssetUrl(value) ?? value);
          } else if (field === "audioUrl") {
            updateSceneTTS(sceneId, prefixAssetUrl(value) ?? value);
          } else if (field === "status") {
            updateSceneStatus(sceneId, value as Scene["status"]);
          } else if (field === "index") {
            updateSceneIndex(sceneId, Number(value));
          }
          break;
        }

        case "error":
          console.debug("[SayCut] error event, resetting to idle");
          setAgentState("idle");
          isProcessing.current = false;
          break;
      }
    },
    [
      setAgentState,
      setStorybookId,
      startAgentMessage,
      appendAgentChunk,
      finalizeAgentMessage,
      addToolStatus,
      addScene,
      clear,
      updateSceneImage,
      updateSceneVideo,
      updateSceneTTS,
      updateSceneStatus,
      updateSceneIndex,
      removeScene,
      selectScene,
      storybookId,
      projectMode,
      projectCharacters,
    ],
  );

  // Store handler in a ref so the WS lifecycle doesn't depend on it
  const handlerRef = useRef(handleMessage);
  handlerRef.current = handleMessage;

  useEffect(() => {
    const client = new WSClient();
    clientRef.current = client;

    let savedSessionId: string | null = null;
    try {
      savedSessionId = sessionStorage.getItem(
        `saycut-session-${storybookId ?? "new"}`,
      );
    } catch {
      // sessionStorage may be unavailable
    }

    client.connect(
      (msg) => handlerRef.current(msg),
      () => {
        // Fired on WS open — guaranteed to be connected
        client.sendSessionInit(savedSessionId ?? undefined);
      },
    );

    return () => {
      client.disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storybookId]);

  const sendAudio = useCallback(
    (base64Wav: string) => {
      if (isProcessing.current) {
        console.debug("[SayCut] sendAudio blocked: still processing");
        return;
      }
      isProcessing.current = true;
      firstSceneAdded.current = false;
      console.debug("[SayCut] sendAudio: isProcessing -> true");

      addUserMessage();
      clientRef.current?.sendAudioData(base64Wav);
    },
    [addUserMessage],
  );

  return { sendAudio, client: clientRef };
}
