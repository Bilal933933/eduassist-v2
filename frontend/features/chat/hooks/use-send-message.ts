"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import {
  RequestFailedError,
  answerInteractionRequest,
  dismissInteractionRequest,
  sendMessageRequest,
} from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";

function errorMessage(error: unknown, fallback: string) {
  return error instanceof RequestFailedError ? error.message : fallback;
}

// ─── الإرسال: القبول من HTTP والرد النهائي من المقبس ───
// عند حدث الاكتمال يُبطل المستدعي استعلام الرسائل فيُعاد الجلب من السيرفر.
export function useSendMessage(conversationId: string) {
  const queryClient = useQueryClient();
  const [isBusy, setIsBusy] = useState(false);

  const mutation = useMutation({
    mutationFn: (content: string) => sendMessageRequest(conversationId, content),
    onError: (error) => {
      toast.error(errorMessage(error, "تعذر إرسال الرسالة."));
      setIsBusy(false);
    },
  });

  const answerMutation = useMutation({
    mutationFn: (payload: {
      interactionId: string;
      answers: Record<string, string>;
      message: string;
    }) =>
      answerInteractionRequest(
        conversationId,
        payload.interactionId,
        payload.answers,
        payload.message,
      ),
    onError: (error) => {
      toast.error(errorMessage(error, "تعذر إرسال الإجابات."));
      setIsBusy(false);
    },
  });

  const dismissMutation = useMutation({
    mutationFn: (interactionId: string) =>
      dismissInteractionRequest(conversationId, interactionId),
    onError: (error) => {
      toast.error(errorMessage(error, "تعذر إغلاق الأسئلة."));
      setIsBusy(false);
    },
  });

  async function send(content: string) {
    const trimmed = content.trim();
    if (!trimmed || isBusy) return;
    setIsBusy(true);
    try {
      await mutation.mutateAsync(trimmed);
    } catch {
      // الخطأ عولج في onError مع تصفير الانشغال.
    }
  }

  async function answerInteraction(
    interactionId: string,
    answers: Record<string, string>,
    message: string,
  ) {
    if (isBusy) return;
    setIsBusy(true);
    try {
      await answerMutation.mutateAsync({ interactionId, answers, message });
    } catch (error) {
      // الخطأ عولج في onError مع تصفير الانشغال.
      throw error;
    }
  }

  async function dismissInteraction(interactionId: string) {
    if (isBusy) return;
    setIsBusy(true);
    try {
      await dismissMutation.mutateAsync(interactionId);
      toast.success("تم إغلاق الأسئلة.");
      await queryClient.invalidateQueries({
        queryKey: queryKeys.messages(conversationId),
      });
      setIsBusy(false);
    } catch (error) {
      // الخطأ عولج في onError مع تصفير الانشغال.
      throw error;
    }
  }

  return {
    send,
    answerInteraction,
    dismissInteraction,
    isBusy,
    setIsBusy,
  };
}
