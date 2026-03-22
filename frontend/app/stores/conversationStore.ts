import { create } from "zustand";
import { Message } from "../lib/types";

interface ConversationStore {
  readonly messages: readonly Message[];
  readonly isStreaming: boolean;
  addUserMessage: () => void;
  startAgentMessage: () => string;
  appendAgentChunk: (id: string, text: string) => void;
  finalizeAgentMessage: (id: string) => void;
  addToolStatus: (name: string, status: string, sceneId?: string) => void;
  loadMessages: (msgs: readonly Message[]) => void;
  clear: () => void;
}

let nextId = 0;
const makeId = () => `msg-${++nextId}-${Date.now()}`;

export const useConversationStore = create<ConversationStore>((set) => ({
  messages: [],
  isStreaming: false,

  addUserMessage: () =>
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id: makeId(),
          role: "user" as const,
          text: "",
          timestamp: Date.now(),
        },
      ],
    })),

  startAgentMessage: () => {
    const id = makeId();
    set((state) => ({
      isStreaming: true,
      messages: [
        ...state.messages,
        {
          id,
          role: "agent" as const,
          text: "",
          timestamp: Date.now(),
          isStreaming: true,
        },
      ],
    }));
    return id;
  },

  appendAgentChunk: (id, text) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, text: m.text + text } : m,
      ),
    })),

  finalizeAgentMessage: (id) =>
    set((state) => ({
      isStreaming: false,
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, isStreaming: false } : m,
      ),
    })),

  addToolStatus: (name, status, sceneId?) =>
    set((state) => {
      const existingIdx = state.messages.findIndex(
        (m) =>
          m.role === "tool" && m.toolName === name && m.toolStatus !== "done",
      );
      if (existingIdx !== -1) {
        return {
          messages: state.messages.map((m, i) =>
            i === existingIdx
              ? {
                  ...m,
                  text: status,
                  toolStatus: status,
                  ...(sceneId ? { sceneId } : {}),
                }
              : m,
          ),
        };
      }
      return {
        messages: [
          ...state.messages,
          {
            id: makeId(),
            role: "tool" as const,
            text: status,
            toolName: name,
            toolStatus: status,
            ...(sceneId ? { sceneId } : {}),
            timestamp: Date.now(),
          },
        ],
      };
    }),

  loadMessages: (msgs) => set({ messages: msgs }),

  clear: () => set({ messages: [], isStreaming: false }),
}));
