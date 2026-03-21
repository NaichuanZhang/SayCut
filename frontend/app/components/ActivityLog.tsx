"use client";

import { useEffect, useRef } from "react";
import { useConversationStore } from "../stores/conversationStore";
import { MessageBubble } from "./MessageBubble";
import { ToolCallCard } from "./ToolCallCard";

export function ActivityLog() {
  const messages = useConversationStore((s) => s.messages);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto px-3 py-3">
      <div className="flex flex-col gap-2">
        {messages.map((msg) =>
          msg.role === "tool" ? (
            <ToolCallCard key={msg.id} message={msg} />
          ) : (
            <MessageBubble key={msg.id} message={msg} compact />
          )
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
