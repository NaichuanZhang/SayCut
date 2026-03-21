"use client";

import { useCallback, useEffect, useRef } from "react";
import { useConversationStore } from "../stores/conversationStore";
import { useStorybookStore } from "../stores/storybookStore";
import { useUIStore } from "../stores/uiStore";
import { WSClient, ServerMessage } from "../lib/wsClient";
import { Scene } from "../lib/types";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:3001";

function prefixAssetUrl(url: string | null): string | null {
  if (!url) return null;
  if (url.startsWith("http")) return url;
  return `${BACKEND_URL}${url}`;
}

export function useAgent() {
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

  const addScene = useStorybookStore((s) => s.addScene);
  const updateSceneImage = useStorybookStore((s) => s.updateSceneImage);
  const updateSceneVideo = useStorybookStore((s) => s.updateSceneVideo);
  const updateSceneTTS = useStorybookStore((s) => s.updateSceneTTS);
  const updateSceneStatus = useStorybookStore((s) => s.updateSceneStatus);

  const setAgentState = useUIStore((s) => s.setAgentState);
  const selectScene = useUIStore((s) => s.selectScene);

  const handleMessage = useCallback(
    (msg: ServerMessage) => {
      console.debug("[SayCut] handleMessage:", msg.type);

      switch (msg.type) {
        case "session_created":
          sessionIdRef.current = msg.session_id as string;
          console.debug(
            "[SayCut] Session created:",
            sessionIdRef.current,
          );
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
          addToolStatus(msg.tool_name as string, msg.status as string);
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
            status: (sceneData.status as Scene["status"]) ?? "empty",
          };
          addScene(scene);
          if (!firstSceneAdded.current) {
            firstSceneAdded.current = true;
            selectScene(scene.id);
          }
          break;
        }

        case "scene_update": {
          const sceneId = msg.scene_id as string;
          const field = msg.field as string;
          const value = msg.value as string;

          if (field === "imageUrl") {
            updateSceneImage(sceneId, prefixAssetUrl(value) ?? value);
          } else if (field === "videoUrl") {
            updateSceneVideo(sceneId, prefixAssetUrl(value) ?? value);
          } else if (field === "audioUrl") {
            updateSceneTTS(sceneId, prefixAssetUrl(value) ?? value);
          } else if (field === "status") {
            updateSceneStatus(sceneId, value as Scene["status"]);
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
      startAgentMessage,
      appendAgentChunk,
      finalizeAgentMessage,
      addToolStatus,
      addScene,
      updateSceneImage,
      updateSceneVideo,
      updateSceneTTS,
      updateSceneStatus,
      selectScene,
    ],
  );

  useEffect(() => {
    const client = new WSClient();
    clientRef.current = client;
    client.connect(handleMessage);

    // Give the WebSocket a moment to connect, then init session
    const timer = setTimeout(() => {
      client.sendSessionInit();
    }, 500);

    return () => {
      clearTimeout(timer);
      client.disconnect();
    };
  }, [handleMessage]);

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
