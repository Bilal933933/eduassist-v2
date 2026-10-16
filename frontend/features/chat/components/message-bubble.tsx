"use client";

import type { ChatMessage } from "@/lib/api";

function formatTime(value: string) {
  return new Date(value).toLocaleTimeString("ar", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.sender === "user";
  return (
    <div className={`flex flex-col gap-1 ${isUser ? "items-start" : "items-end"}`}>
      <p
        className={`max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-7 ${
          isUser ? "bg-emerald-700 text-white" : "border bg-white text-slate-800"
        }`}
      >
        {message.content}
      </p>
      <span className="px-1 text-[11px] text-slate-400">
        {formatTime(message.created_at)}
      </span>
    </div>
  );
}
