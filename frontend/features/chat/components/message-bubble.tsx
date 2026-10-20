"use client";

import type { ChatMessage } from "@/lib/api";
import { ResponseMetadata } from "@/features/chat/components/response-metadata";
import { RichText } from "@/features/chat/components/rich-text";

function formatTime(value: string) {
  return new Date(value).toLocaleTimeString("ar", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.sender === "user";
  return (
    <div
      className={`group flex w-full flex-col gap-1 ${
        isUser ? "items-start" : "items-end"
      }`}
    >
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-[15px] leading-8 ${
          isUser
            ? "bg-emerald-700 text-white shadow-sm"
            : "border border-slate-200 bg-white text-slate-800 shadow-sm"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap text-pretty">{message.content}</p>
        ) : (
          <RichText content={message.content} />
        )}
      </div>
      <div className="flex items-center gap-2 px-1">
        <span className="text-[11px] tabular-nums text-slate-400">
          {formatTime(message.created_at)}
        </span>
        {!isUser && message.metadata && (
          <ResponseMetadata metadata={message.metadata} />
        )}
      </div>
    </div>
  );
}
