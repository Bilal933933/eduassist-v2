"use client";

import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Sparkles, BookOpen, HelpCircle, MessageSquarePlus, Lightbulb, Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
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
    <section className="flex h-full w-full flex-col overflow-hidden bg-background">
      <div className="shrink-0 border-b border-border bg-background/80 backdrop-blur-sm">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="flex min-w-0 items-center gap-2">
            <Button
              size="icon"
              variant="ghost"
              className="shrink-0 rounded-xl text-muted-foreground hover:bg-muted hover:text-foreground"
              onClick={toggleSidebar}
              aria-label={isSidebarOpen ? "إغلاق القائمة الجانبية" : "فتح القائمة الجانبية"}
              title={isSidebarOpen ? "إغلاق القائمة الجانبية" : "فتح القائمة الجانبية"}
            >
              <Menu className="size-5" />
            </Button>

            <h1 className="truncate text-sm font-bold text-foreground">
              محادثة جديدة
            </h1>
          </div>

          <div className="flex shrink-0 items-center gap-1">
            <ThemeToggle />
          </div>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto bg-background">
        <div className="mx-auto flex w-full max-w-3xl flex-col items-center justify-center p-6 pb-12 text-center min-h-[calc(100%-2rem)]">
          <div className="mb-4 flex size-16 items-center justify-center rounded-3xl bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 shadow-sm">
            <Sparkles className="size-8" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            أهلاً بك، كيف يمكنني مساعدتك في النحو؟
          </h1>
          <p className="mt-2 max-w-md text-muted-foreground">
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
                  className="flex items-start gap-3.5 rounded-2xl border border-border bg-muted/40 p-4 text-right transition-all hover:border-emerald-300 dark:hover:border-emerald-500/40 hover:bg-emerald-50/30 dark:hover:bg-emerald-500/10 hover:shadow-md disabled:opacity-50"
                >
                  <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-background text-emerald-600 dark:text-emerald-400 shadow-sm">
                    <Icon className="size-5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-foreground">
                      {item.title}
                    </p>
                    <p className="mt-0.5 line-clamp-2 text-xs leading-5 text-muted-foreground">
                      {item.prompt}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>
      <div className="shrink-0 bg-background">
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
