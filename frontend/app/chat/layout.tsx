"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Skeleton } from "@/components/ui/skeleton";
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

  useEffect(() => {
    if (!me.isPending && !me.data) router.replace("/login");
  }, [me.isPending, me.data, router]);

  if (me.isPending) {
    return (
      <main className="flex h-dvh items-center justify-center bg-slate-50" dir="rtl">
        <Skeleton className="h-64 w-full max-w-md rounded-3xl" />
      </main>
    );
  }

  if (!me.data) return null;

  return (
    <main className="flex h-dvh w-full overflow-hidden bg-slate-50/50" dir="rtl">
      {/* سطح المكتب: شريط قابل للطي بنعومة */}
      <aside
        className={`hidden shrink-0 border-l border-slate-100 bg-slate-50/60 transition-all duration-300 ease-in-out md:block ${
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
            className="w-72 gap-0 border-l-slate-100 p-0"
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
      <div className="flex h-full min-w-0 flex-1 flex-col overflow-hidden bg-white">
        {children}
      </div>
    </main>
  );
}
