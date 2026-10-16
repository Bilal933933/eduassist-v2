"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, use, useEffect, useRef } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { MessageBubble } from "@/features/chat/components/message-bubble";
import { MessageInput } from "@/features/chat/components/message-input";
import { TypingIndicator } from "@/features/chat/components/typing-indicator";
import { useChatSocket } from "@/features/chat/hooks/use-chat-socket";
import { useMessages } from "@/features/chat/hooks/use-messages";
import { useSendMessage } from "@/features/chat/hooks/use-send-message";
import { useConversation } from "@/features/conversations/hooks/use-conversations";
import { RequestFailedError } from "@/lib/api";

function ConversationView({ conversationId }: { conversationId: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const pendingSent = useRef(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);

  const messages = useMessages(conversationId);
  const { conversation } = useConversation(conversationId);
  const { send, isBusy, setIsBusy } = useSendMessage(conversationId);
  const { isConnected } = useChatSocket(conversationId, () => setIsBusy(false));

  // رسالة قادمة من صفحة "جديد": تُرسل مرة واحدة بعد اتصال المقبس.
  useEffect(() => {
    const pending = searchParams.get("message");
    if (!pending || pendingSent.current || !isConnected || isBusy) return;
    pendingSent.current = true;
    send(pending).catch(() => {
      pendingSent.current = false;
    });
    router.replace(`/chat/${conversationId}`);
  }, [searchParams, isConnected, isBusy, send, router, conversationId]);

  const items = messages.data?.pages.flatMap((page) => page.items) ?? [];

  // تمرير تلقائي للأسفل مع الجديد، ما لم يصعد المستخدم لقراءة الأقدم.
  useEffect(() => {
    const container = scrollRef.current;
    if (container && stickToBottom.current) {
      container.scrollTop = container.scrollHeight;
    }
  }, [items.length, isBusy]);

  function handleScroll() {
    const container = scrollRef.current;
    if (!container) return;
    const distanceFromBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight;
    stickToBottom.current = distanceFromBottom < 120;
  }

  if (messages.isPending) {
    return (
      <section className="w-full max-w-4xl">
        <Skeleton className="h-[60vh] w-full" />
      </section>
    );
  }

  if (messages.isError) {
    const error = messages.error;
    return (
      <section className="w-full max-w-4xl rounded-3xl border bg-white p-8 text-center shadow-xl">
        <p className="font-semibold text-red-700">
          {error instanceof RequestFailedError ? error.message : "تعذر تحميل المحادثة."}
        </p>
        <Button className="mt-4" onClick={() => messages.refetch()}>
          إعادة المحاولة
        </Button>
      </section>
    );
  }

  return (
    <section className="flex w-full max-w-4xl flex-col overflow-hidden rounded-3xl border bg-white shadow-xl">
      <div className="flex items-center justify-between gap-3 border-b px-6 py-3">
        <h1 className="truncate text-sm font-bold text-slate-900">
          {conversation?.title ?? "محادثة بلا عنوان"}
        </h1>
        <div className="flex shrink-0 items-center gap-2">
          {messages.hasNextPage && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => messages.fetchNextPage()}
              disabled={messages.isFetchingNextPage}
            >
              {messages.isFetchingNextPage ? "جارٍ التحميل..." : "عرض المزيد"}
            </Button>
          )}
          <span
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              isConnected
                ? "bg-emerald-100 text-emerald-700"
                : "bg-amber-100 text-amber-700"
            }`}
          >
            {isConnected ? "متصل" : "جارٍ الاتصال"}
          </span>
        </div>
      </div>

      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="min-h-[60vh] flex-1 space-y-4 overflow-y-auto bg-slate-50 p-6"
      >
        {items.length === 0 && (
          <div className="mx-auto mt-20 max-w-md text-center text-slate-500">
            <p className="text-lg font-semibold text-slate-700">لا رسائل بعد</p>
            <p className="mt-2 text-sm">ابدأ بسؤال بسيط.</p>
          </div>
        )}
        {items.map((item) => (
          <MessageBubble key={item.id} message={item} />
        ))}
        {isBusy && <TypingIndicator />}
      </div>

      <MessageInput
        disabled={!isConnected || isBusy}
        onSend={(content) =>
          send(content).catch(() => toast.error("تعذر إرسال الرسالة."))
        }
      />
    </section>
  );
}

export default function ConversationPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  return (
    <Suspense>
      <ConversationView conversationId={id} />
    </Suspense>
  );
}
