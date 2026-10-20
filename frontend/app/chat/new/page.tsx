"use client";

import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Sparkles, BookOpen, HelpCircle, MessageSquarePlus, Lightbulb, Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { MessageInput } from "@/features/chat/components/message-input";
import { RequestFailedError } from "@/lib/api";
import { useCreateConversation } from "@/features/conversations/hooks/use-conversations";
import { useSidebarStore } from "@/features/chat/stores/sidebar-store";

const SUGGESTIONS = [
  {
    title: "شرح قواعد",
    prompt: "اشرح لي الفرق بين الفاعل ونائب الفاعل بأمثلة واضحة",
    icon: BookOpen,
  },
  {
    title: "علامات الإعراب",
    prompt: "ما هي علامات نصب المفعول به في الأسماء المختلفة؟",
    icon: HelpCircle,
  },
  {
    title: "أمثلة نحوية",
    prompt: "أعطني مثالًا تفصيليًا على إعراب جملة فيها كان وأخواتها",
    icon: Lightbulb,
  },
  {
    title: "تحضير درساً",
    prompt: "حضّر لي درسًا مبسطًا عن المفعول به لتقديمه للطلاب",
    icon: MessageSquarePlus,
  },
];

function titleFrom(content: string) {
  const trimmed = content.trim().replace(/\s+/g, " ");
  return trimmed.length > 40 ? `${trimmed.slice(0, 40)}...` : trimmed;
}

export default function NewChatPage() {
  const router = useRouter();
  const createConversation = useCreateConversation();
  const toggleSidebar = useSidebarStore((state) => state.toggle);
  const isSidebarOpen = useSidebarStore((state) => state.isOpen);

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
    <section className="flex h-full w-full flex-col overflow-hidden bg-white">
      <div className="shrink-0 border-b border-slate-100 bg-white/80 backdrop-blur-sm">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="flex min-w-0 items-center gap-2">
            <Button
              size="icon"
              variant="ghost"
              className="shrink-0 rounded-xl text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              onClick={toggleSidebar}
              aria-label={isSidebarOpen ? "إغلاق القائمة الجانبية" : "فتح القائمة الجانبية"}
              title={isSidebarOpen ? "إغلاق القائمة الجانبية" : "فتح القائمة الجانبية"}
            >
              <Menu className="size-5" />
            </Button>

            <h1 className="truncate text-sm font-bold text-slate-900">
              محادثة جديدة
            </h1>
          </div>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto bg-white">
        <div className="mx-auto flex w-full max-w-3xl flex-col items-center justify-center p-6 pb-12 text-center min-h-[calc(100%-2rem)]">
          <div className="mb-4 flex size-16 items-center justify-center rounded-3xl bg-emerald-50 text-emerald-600 shadow-sm">
            <Sparkles className="size-8" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
            أهلاً بك، كيف يمكنني مساعدتك في النحو؟
          </h1>
          <p className="mt-2 max-w-md text-slate-500">
            اطرح سؤالك النحوي أو اختر أحد الاقتراحات أدناه للبدء فوراً.
          </p>

          <div className="mt-8 grid w-full grid-cols-1 gap-3 sm:grid-cols-2">
            {SUGGESTIONS.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.title}
                  type="button"
                  onClick={() => void handleFirstMessage(item.prompt)}
                  disabled={createConversation.isPending}
                  className="flex items-center gap-3.5 rounded-2xl border border-slate-200/80 bg-slate-50/50 p-4 text-right transition-all hover:border-emerald-300 hover:bg-emerald-50/30 hover:shadow-md disabled:opacity-50"
                >
                  <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-white text-emerald-600 shadow-sm">
                    <Icon className="size-5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-slate-800">
                      {item.title}
                    </p>
                    <p className="truncate text-xs text-slate-500">
                      {item.prompt}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>
      <div className="shrink-0 bg-white">
        <MessageInput
          disabled={createConversation.isPending}
          disabledReason={
            createConversation.isPending ? "جارٍ إنشاء المحادثة..." : undefined
          }
          onSend={handleFirstMessage}
        />
      </div>
    </section>
  );
}
