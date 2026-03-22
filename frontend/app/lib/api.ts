import { CharacterConfig, DialogueLine, Scene, StoryMode } from "./types";

const BASE = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:3001";

export interface StorybookSummary {
  readonly id: string;
  readonly title: string;
  readonly mode: StoryMode;
  readonly characters?: readonly CharacterConfig[] | null;
  readonly createdAt: string;
  readonly thumbnailUrl: string | null;
  readonly sceneCount: number;
}

export interface StorybookDetail {
  readonly id: string;
  readonly title: string;
  readonly mode: StoryMode;
  readonly characters?: readonly CharacterConfig[] | null;
  readonly sessionId: string;
  readonly createdAt: string;
  readonly scenes: readonly Scene[];
}

export async function fetchStorybooks(): Promise<StorybookSummary[]> {
  const res = await fetch(`${BASE}/api/storybooks`);
  if (!res.ok) throw new Error("Failed to fetch storybooks");
  return res.json();
}

export async function fetchStorybook(id: string): Promise<StorybookDetail> {
  const res = await fetch(`${BASE}/api/storybooks/${encodeURIComponent(id)}`);
  if (!res.ok) throw new Error("Failed to fetch storybook");
  return res.json();
}

export interface MessageRecord {
  readonly id: string;
  readonly role: string;
  readonly text: string;
  readonly createdAt: string;
}

export async function fetchMessages(
  storybookId: string,
): Promise<MessageRecord[]> {
  const res = await fetch(
    `${BASE}/api/storybooks/${encodeURIComponent(storybookId)}/messages`,
  );
  if (!res.ok) throw new Error("Failed to fetch messages");
  return res.json();
}
