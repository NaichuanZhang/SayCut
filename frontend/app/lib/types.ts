export type AgentState = "idle" | "listening" | "thinking" | "speaking";

export interface DialogueLine {
  readonly character: string;
  readonly text: string;
}

export interface CharacterConfig {
  readonly name: string;
  readonly voice: string;
}

export interface Message {
  readonly id: string;
  readonly role: "user" | "agent" | "tool";
  readonly text: string;
  readonly timestamp: number;
  readonly isStreaming?: boolean;
  readonly toolName?: string;
  readonly toolStatus?: string;
  readonly sceneId?: string;
}

export interface Scene {
  readonly id: string;
  readonly index: number;
  readonly title: string;
  readonly narrationText: string;
  readonly visualDescription: string;
  readonly imageUrl: string | null;
  readonly videoUrl: string | null;
  readonly audioUrl: string | null;
  readonly dialogueLines?: readonly DialogueLine[];
  readonly status: "empty" | "generating" | "ready";
}

export type StoryMode = "story" | "movie";

export interface Storybook {
  readonly id: string;
  readonly title: string;
  readonly mode?: StoryMode;
  readonly characters?: readonly CharacterConfig[];
  readonly scenes: readonly Scene[];
}
