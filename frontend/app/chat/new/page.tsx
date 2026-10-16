"use client";

import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { MessageInput } from "@/features/chat/components/message-input";
import { RequestFailedError } from "@/lib/api";
import { useCreateConversation } from "@/features/conversations/hooks/use-conversations";

function titleFrom(content: string) {
  const trimmed = content.trim().replace(/\s+/g, " ");
  return trimmed.length > 40 ? `${trimmed.slice(0, 40)}...` : trimmed;
}

export default function NewChatPage() {
  const router = useRouter();
  const createConversation = useCreateConversation();

  async function handleFirstMessage(content: string) {
    try {
      const conversation = await createConversation.mutateAsync(titleFrom(content));
      router.replace(`/chat/${conversation.id}?message=${encodeURIComponent(content)}`);
    } catch (error) {
      toast.error(
        error instanceof RequestFailedError ? error.message : "تعذر بدء المحادثة.",
      );
    }
  }

  return (
    <section className="flex w-full max-w-4xl flex-col overflow-hidden rounded-3xl border bg-white shadow-xl">
      <div className="flex min-h-[60vh] flex-1 flex-col items-center justify-center gap-2 bg-slate-50 p-6 text-center">
        <p className="text-lg font-semibold text-slate-700">محادثة جديدة</p>
        <p className="max-w-md text-sm text-slate-500">
          اكتب أول رسالة — تُنشأ المحادثة عند الإرسال فقط. مثال: اشرح لي الفرق بين
          الفاعل ونائب الفاعل.
        </p>
      </div>
      <MessageInput
        disabled={createConversation.isPending}
        onSend={handleFirstMessage}
      />
    </section>
  );
}
