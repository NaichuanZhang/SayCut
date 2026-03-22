"use client";

import { createContext, useContext } from "react";

interface EditorContextValue {
  readonly storybookId: string | undefined;
}

export const EditorContext = createContext<EditorContextValue>({
  storybookId: undefined,
});

export function useEditorContext() {
  return useContext(EditorContext);
}
