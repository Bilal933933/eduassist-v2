"use client";

import { Sparkles } from "lucide-react";
import type { ChatMessage } from "@/lib/api";
import { QuestionCard } from "@/features/chat/components/question-card";
import { ResponseMetadata } from "@/features/chat/components/response-metadata";
import { RichText } from "@/features/chat/components/rich-text";

function formatTime(value: string) {
  return new Date(value).toLocaleTimeString("ar", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

type MessageBubbleProps = {
  message: ChatMessage;
  isBusy?: boolean;
  onAnswer?: (
    interactionId: string,
    answers: Record<string, string>,
    message: string,
  ) => Promise<void>;
  onDismiss?: (interactionId: string) => Promise<void>;
};

export function MessageBubble({
  message,
  isBusy = false,
  onAnswer,
  onDismiss,
}: MessageBubbleProps) {
  const isUser = message.sender === "user";
  return (
    <div className="my-6 flex w-full flex-col gap-4">
      <div
        className={`flex w-full gap-3 ${
          isUser ? "flex-row-reverse justify-start" : "flex-row justify-start"
        }`}
      >
        {!isUser && (
          <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 shadow-sm">
            <Sparkles className="size-4" />
          </div>
        )}
        <div
          className={`flex max-w-[85%] flex-col gap-2 ${
            isUser ? "items-end" : "items-start"
          }`}
        >
          <div
            className={`rounded-3xl px-5 py-3.5 text-[15px] leading-8 shadow-sm ${
              isUser
                ? "bg-slate-100 text-slate-900 rounded-bl-sm"
                : "bg-transparent px-0 py-1 text-slate-800 shadow-none"
            }`}
          >
            {isUser ? (
              <p className="whitespace-pre-wrap text-pretty">{message.content}</p>
            ) : (
              <RichText content={message.content} />
            )}
          </div>
          <div className="px-1">
            <span className="text-[11px] tabular-nums text-slate-400">
              {formatTime(message.created_at)}
            </span>
          </div>
        </div>
      </div>

      {!isUser && message.interaction && onAnswer && onDismiss && (
        <div className="flex w-full justify-start pl-11">
          <QuestionCard
            interactionId={message.id}
            interaction={message.interaction}
            disabled={isBusy}
            onAnswer={onAnswer}
            onDismiss={onDismiss}
          />
        </div>
      )}

      {/* عرض الميتا داتا في سطر مستقل تماماً أسفل فقاعة الرد */}
      {!isUser && message.metadata && (
        <div className="flex w-full justify-center border-t border-slate-100 pt-2">
          <ResponseMetadata metadata={message.metadata} />
        </div>
      )}
    </div>
  );
}
