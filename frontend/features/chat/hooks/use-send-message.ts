"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { RequestFailedError, sendMessageRequest } from "@/lib/api";

// ─── الإرسال: القبول من HTTP والرد النهائي من المقبس ───
// عند حدث الاكتمال يُبطل المستدعي استعلام الرسائل فيُعاد الجلب من السيرفر.
export function useSendMessage(conversationId: string) {
  const [isBusy, setIsBusy] = useState(false);

  const mutation = useMutation({
    mutationFn: (content: string) => sendMessageRequest(conversationId, content),
    onError: (error) => {
      toast.error(
        error instanceof RequestFailedError ? error.message : "تعذر إرسال الرسالة.",
      );
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

  return { send, isBusy, setIsBusy };
}
