"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, use, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { ArrowDown, Menu, Plus, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { MessageBubble } from "@/features/chat/components/message-bubble";
import { MessageInput } from "@/features/chat/components/message-input";
import { TypingIndicator } from "@/features/chat/components/typing-indicator";
import { useChatSocket } from "@/features/chat/hooks/use-chat-socket";
import { useMessages } from "@/features/chat/hooks/use-messages";
import { useSendMessage } from "@/features/chat/hooks/use-send-message";
import { useSidebarStore } from "@/features/chat/stores/sidebar-store";
import { useConversation } from "@/features/conversations/hooks/use-conversations";
import { RequestFailedError } from "@/lib/api";

const SUGGESTIONS = [
  "اشرح لي الفرق بين الفاعل ونائب الفاعل",
  "ما علامات نصب المفعول به؟",
  "أعطني مثالًا على كان وأخواتها",
];

function ConversationView({ conversationId }: { conversationId: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const pendingSent = useRef(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);
  const [showScrollButton, setShowScrollButton] = useState(false);

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
    setShowScrollButton(distanceFromBottom > 240);
  }

  function scrollToBottom() {
    const container = scrollRef.current;
    if (!container) return;
    stickToBottom.current = true;
    setShowScrollButton(false);
    container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
  }

  if (messages.isPending) {
    return (
      <section className="flex h-[calc(100dvh-2rem)] w-full max-w-4xl flex-col overflow-hidden rounded-3xl border bg-white shadow-xl sm:h-[calc(100dvh-4rem)]">
        <Skeleton className="h-full w-full" />
      </section>
    );
  }

  if (messages.isError) {
    const error = messages.error;
    return (
      <section className="flex h-[calc(100dvh-2rem)] w-full max-w-4xl flex-col items-center justify-center gap-4 rounded-3xl border bg-white p-8 text-center shadow-xl sm:h-[calc(100dvh-4rem)]">
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
    <section className="relative flex h-[calc(100dvh-2rem)] w-full max-w-4xl flex-col overflow-hidden rounded-3xl border bg-white shadow-xl sm:h-[calc(100dvh-4rem)]">
      <div className="flex items-center justify-between gap-3 border-b px-4 py-3 sm:px-6">
        <div className="flex min-w-0 items-center gap-2">
          <Button
            size="icon"
            variant="ghost"
            className="shrink-0 md:hidden"
            onClick={() => useSidebarStore.getState().open()}
            aria-label="فتح قائمة المحادثات"
          >
            <Menu className="size-5" />
          </Button>
          <h1 className="truncate text-sm font-bold text-slate-900">
            {conversation?.title ?? "محادثة بلا عنوان"}
          </h1>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {messages.hasNextPage && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => messages.fetchNextPage()}
              disabled={messages.isFetchingNextPage}
            >
              {messages.isFetchingNextPage ? "جارٍ التحميل..." : "عرض الأقدم"}
            </Button>
          )}
          <Button
            size="icon"
            variant="ghost"
            onClick={() => router.push("/chat/new")}
            aria-label="محادثة جديدة"
          >
            <Plus className="size-5" />
          </Button>
          <span
            className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
              isConnected
                ? "bg-emerald-100 text-emerald-700"
                : "bg-amber-100 text-amber-700"
            }`}
            aria-label={isConnected ? "متصل بالمحادثة" : "جارٍ الاتصال"}
          >
            <span className="size-1.5 rounded-full bg-current" />
            <span className="hidden sm:inline">
              {isConnected ? "متصل" : "جارٍ الاتصال"}
            </span>
          </span>
        </div>
      </div>

      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 space-y-4 overflow-y-auto overscroll-contain bg-slate-50 px-4 py-5 sm:px-6"
      >
        {items.length === 0 && (
          <div className="mx-auto mt-16 max-w-md text-center">
            <div className="mx-auto flex size-12 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-700">
              <Sparkles className="size-6" />
            </div>
            <p className="mt-3 text-base font-semibold text-slate-800">
              ابدأ المحادثة بسؤال
            </p>
            <p className="mt-1 text-sm text-slate-500">
              اسأل عن قاعدة نحوية، أو اطلب مثالًا، أو اطلب تحضير درس.
            </p>
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => send(suggestion)}
                  className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 transition-colors hover:border-emerald-300 hover:text-emerald-700"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}
        {items.map((item) => (
          <MessageBubble key={item.id} message={item} />
        ))}
        {isBusy && <TypingIndicator />}
      </div>

      {showScrollButton && (
        <Button
          size="icon"
          variant="outline"
          onClick={scrollToBottom}
          aria-label="التمرير إلى آخر الرسائل"
          className="absolute bottom-24 left-1/2 -translate-x-1/2 rounded-full bg-white shadow-md"
        >
          <ArrowDown className="size-4" />
        </Button>
      )}

      <MessageInput
        disabled={!isConnected || isBusy}
        disabledReason={
          !isConnected
            ? "جارٍ الاتصال بالمحادثة..."
            : isBusy
              ? "يكتب المساعد ردّه..."
              : undefined
        }
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
