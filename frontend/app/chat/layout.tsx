"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { RequestFailedError } from "@/lib/api";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetTitle,
} from "@/components/ui/sheet";
import { useMe } from "@/features/auth/hooks/use-auth";
import { useSidebarStore } from "@/features/chat/stores/sidebar-store";
import { ConversationList } from "@/features/conversations/components/conversation-list";
import { useIsMobile } from "@/hooks/use-mobile";

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const me = useMe();
  const isMobile = useIsMobile();
  const isSidebarOpen = useSidebarStore((state) => state.isOpen);
  const closeSidebar = useSidebarStore((state) => state.close);

  // جلسة منتهية (401) تُحوَّل لتسجيل الدخول، أما تعذّر الوصول للخادم فيُعرض كخطأ قابل لإعادة المحاولة.
  const isUnauthorized =
    me.error instanceof RequestFailedError && me.error.code === "HTTP_401";

  useEffect(() => {
    if (!me.isPending && (isUnauthorized || (!me.data && !me.isError))) {
      router.replace("/login");
    }
  }, [me.isPending, me.data, me.isError, isUnauthorized, router]);

  if (me.isPending || isUnauthorized) {
    return (
      <main className="flex h-dvh items-center justify-center bg-muted" dir="rtl">
        <Skeleton className="h-64 w-full max-w-md rounded-3xl" />
      </main>
    );
  }

  if (me.isError) {
    return (
      <main className="flex h-dvh items-center justify-center bg-muted p-6" dir="rtl">
        <section className="w-full max-w-md rounded-3xl border border-border bg-background p-6 text-center shadow-sm">
          <p className="text-base font-bold text-foreground">تعذر تحميل حسابك</p>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            قد يكون الخادم متوقفًا مؤقتًا. تحقق من الاتصال ثم أعد المحاولة.
          </p>
          <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
            <Button
              className="rounded-xl"
              onClick={() => me.refetch()}
              disabled={me.isFetching}
            >
              {me.isFetching ? "جارٍ المحاولة..." : "إعادة المحاولة"}
            </Button>
            <Button
              variant="outline"
              className="rounded-xl"
              onClick={() => router.replace("/login")}
            >
              تسجيل الدخول
            </Button>
          </div>
        </section>
      </main>
    );
  }

  if (!me.data) {
    return (
      <main className="flex h-dvh items-center justify-center bg-muted" dir="rtl">
        <Skeleton className="h-64 w-full max-w-md rounded-3xl" />
      </main>
    );
  }

  return (
    <main className="flex h-dvh w-full overflow-hidden bg-muted/40" dir="rtl">
      {/* سطح المكتب: شريط قابل للطي بنعومة */}
      <aside
        className={`hidden shrink-0 border-l border-border bg-muted/50 transition-all duration-300 ease-in-out md:block ${
          isSidebarOpen ? "w-72" : "w-0 overflow-hidden border-l-0"
        }`}
      >
        <div className="h-full w-72">
          <ConversationList
            userName={me.data.full_name}
            userRole={me.data.role}
          />
        </div>
      </aside>

      {/* الجوال: درج بمكوّن Sheet يفتح فقط على الشاشات الصغيرة */}
      {isMobile && (
        <Sheet
          open={isSidebarOpen}
          onOpenChange={(open) => {
            if (!open) closeSidebar();
          }}
        >
          <SheetContent
            side="right"
            className="w-72 gap-0 border-l-border p-0"
            showCloseButton={false}
          >
            <SheetTitle className="sr-only">قائمة المحادثات</SheetTitle>
            <SheetDescription className="sr-only">
              اختر محادثة لعرضها أو ابدأ محادثة جديدة.
            </SheetDescription>
            <ConversationList
              userName={me.data.full_name}
              userRole={me.data.role}
              onSelect={closeSidebar}
              className="w-full"
            />
          </SheetContent>
        </Sheet>
      )}

      {/* منطقة المحتوى الرئيسية */}
      <div className="flex h-full min-w-0 flex-1 flex-col overflow-hidden bg-background">
        {children}
      </div>
    </main>
  );
}
