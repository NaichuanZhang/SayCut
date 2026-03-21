import { MOCK_SCENES, MOCK_AGENT_RESPONSES } from "./mockData";
import { Scene } from "./types";

export interface MockAgentCallbacks {
  onThinking: () => void;
  onStreamStart: () => string;
  onStreamChunk: (id: string, char: string) => void;
  onStreamEnd: (id: string) => void;
  onToolStatus: (name: string, status: string) => void;
  onSceneAdd: (scene: Scene) => void;
  onSceneStatusUpdate: (sceneId: string, status: Scene["status"]) => void;
  onSceneImageReady: (sceneId: string, imageUrl: string) => void;
  onSpeaking: () => void;
  onIdle: () => void;
}

async function streamText(
  text: string,
  messageId: string,
  callbacks: MockAgentCallbacks,
  charDelay = 30
): Promise<void> {
  for (const char of text) {
    callbacks.onStreamChunk(messageId, char);
    await delay(charDelay);
  }
  callbacks.onStreamEnd(messageId);
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

let interactionCount = 0;

export async function handleMockInteraction(
  callbacks: MockAgentCallbacks
): Promise<void> {
  const currentInteraction = interactionCount++;

  // Thinking phase
  callbacks.onThinking();
  await delay(800);

  if (currentInteraction === 0) {
    // First interaction: generate script + scenes
    const msgId = callbacks.onStreamStart();
    callbacks.onSpeaking();
    await streamText(MOCK_AGENT_RESPONSES.firstInteraction, msgId, callbacks);
    await delay(400);

    // Tool call: generate script
    callbacks.onToolStatus("generate_script", "Generating script...");
    await delay(2000);
    callbacks.onToolStatus(
      "generate_script",
      'Script ready — "The Whispering Forest" (4 scenes)'
    );
    await delay(300);

    // Stream script-ready message
    const msg2Id = callbacks.onStreamStart();
    await streamText(MOCK_AGENT_RESPONSES.scriptReady, msg2Id, callbacks);
    await delay(500);

    // Add scenes as empty, then generate images with staggered delays
    for (const mockScene of MOCK_SCENES) {
      const emptyScene: Scene = {
        ...mockScene,
        imageUrl: null,
        status: "empty",
      };
      callbacks.onSceneAdd(emptyScene);
    }

    await delay(300);

    // Generate images one by one
    for (let i = 0; i < MOCK_SCENES.length; i++) {
      const scene = MOCK_SCENES[i];
      callbacks.onSceneStatusUpdate(scene.id, "generating");
      callbacks.onToolStatus(
        "generate_scene_image",
        `Generating image for Scene ${i + 1}...`
      );
      await delay(1500 + Math.random() * 1000);
      callbacks.onSceneImageReady(scene.id, scene.imageUrl!);
    }

    await delay(300);
    const msg3Id = callbacks.onStreamStart();
    await streamText(MOCK_AGENT_RESPONSES.followUp, msg3Id, callbacks);
  } else {
    // Subsequent interactions: random contextual response
    const responses = MOCK_AGENT_RESPONSES.genericResponses;
    const text = responses[currentInteraction % responses.length];
    const msgId = callbacks.onStreamStart();
    callbacks.onSpeaking();
    await streamText(text, msgId, callbacks);
  }

  callbacks.onIdle();
}

export function resetMockAgent(): void {
  interactionCount = 0;
}
