"use client";

import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Sparkles } from "lucide-react";
import { MessageInput } from "@/features/chat/components/message-input";
import { RequestFailedError } from "@/lib/api";
import { useCreateConversation } from "@/features/conversations/hooks/use-conversations";

const SUGGESTIONS = [
  "اشرح لي الفرق بين الفاعل ونائب الفاعل",
  "ما علامات نصب المفعول به؟",
  "أعطني مثالًا على كان وأخواتها",
  "حضّر لي درسًا عن المفعول به",
];

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
      throw error;
    }
  }

  return (
    <section className="flex h-[calc(100dvh-2rem)] w-full max-w-4xl flex-col overflow-hidden rounded-3xl border bg-white shadow-xl sm:h-[calc(100dvh-4rem)]">
      <div className="flex flex-1 flex-col items-center justify-center gap-3 bg-slate-50 p-6 text-center">
        <div className="flex size-12 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-700">
          <Sparkles className="size-6" />
        </div>
        <p className="text-lg font-semibold text-slate-800">محادثة جديدة</p>
        <p className="max-w-md text-pretty text-sm text-slate-500">
          اكتب أول رسالة — تُنشأ المحادثة عند الإرسال فقط.
        </p>
        <div className="mt-2 flex max-w-lg flex-wrap justify-center gap-2">
          {SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => void handleFirstMessage(suggestion)}
              disabled={createConversation.isPending}
              className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 transition-colors hover:border-emerald-300 hover:text-emerald-700 disabled:opacity-50"
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>
      <MessageInput
        disabled={createConversation.isPending}
        disabledReason={
          createConversation.isPending ? "جارٍ إنشاء المحادثة..." : undefined
        }
        onSend={handleFirstMessage}
      />
    </section>
  );
}
