/** Remove <tool_call>...</tool_call> blocks and collapse leftover whitespace. */
export function stripToolCalls(text: string): string {
  return text
    .replace(/<tool_call>[\s\S]*?<\/tool_call>/g, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}
