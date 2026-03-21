export type AgentState = "idle" | "listening" | "thinking" | "speaking";

export interface Message {
  readonly id: string;
  readonly role: "user" | "agent" | "tool";
  readonly text: string;
  readonly timestamp: number;
  readonly isStreaming?: boolean;
  readonly toolName?: string;
  readonly toolStatus?: string;
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
  readonly status: "empty" | "generating" | "ready";
}

export interface Storybook {
  readonly id: string;
  readonly title: string;
  readonly scenes: readonly Scene[];
}
