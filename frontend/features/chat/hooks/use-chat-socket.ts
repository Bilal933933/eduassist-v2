"use client";

import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { socketUrlFor } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";

type ChatEvent = {
  type: "chat.started" | "chat.completed" | "chat.failed";
  data:
    | {
        response?: string;
        conversation_id?: string;
        metadata?: Record<string, unknown>;
      }
    | null;
  error: { code?: string; message?: string } | null;
};

// ─── قناة الأحداث (نقل لا جلب — useEffect مسموح هنا) ───
// عند الاكتمال أو الفشل يُبطل استعلام الرسائل ويُصفّر الانشغال عبر onSettled.
export function useChatSocket(
  conversationId: string | null,
  onSettled: () => void,
) {
  const queryClient = useQueryClient();
  const [isConnected, setIsConnected] = useState(false);
  const settledRef = useRef(onSettled);

  useEffect(() => {
    settledRef.current = onSettled;
  }, [onSettled]);

  useEffect(() => {
    if (!conversationId) return;

    const socket = new WebSocket(socketUrlFor(conversationId));
    let closed = false;

    socket.onopen = () => {
      if (!closed) setIsConnected(true);
    };
    socket.onclose = () => {
      if (!closed) setIsConnected(false);
    };
    socket.onerror = () => {
      toast.error("تعذر فتح قناة المحادثة اللحظية.");
    };
    socket.onmessage = (event) => {
      const chatEvent = JSON.parse(event.data) as ChatEvent;
      if (chatEvent.type === "chat.completed") {
        queryClient.invalidateQueries({
          queryKey: queryKeys.messages(conversationId),
        });
        settledRef.current();
      }
      if (chatEvent.type === "chat.failed") {
        queryClient.invalidateQueries({
          queryKey: queryKeys.messages(conversationId),
        });
        toast.error(chatEvent.error?.message ?? "تعذر إكمال المحادثة.");
        settledRef.current();
      }
    };

    return () => {
      closed = true;
      socket.close();
    };
  }, [conversationId, queryClient]);

  return { isConnected };
}
