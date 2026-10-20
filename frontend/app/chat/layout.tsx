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

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const me = useMe();
  const isSidebarOpen = useSidebarStore((state) => state.isOpen);
  const closeSidebar = useSidebarStore((state) => state.close);

  useEffect(() => {
    if (!me.isPending && !me.data) router.replace("/login");
  }, [me.isPending, me.data, router]);

  if (me.isPending) {
    return (
      <main className="flex min-h-dvh items-center justify-center" dir="rtl">
        <Skeleton className="h-64 w-full max-w-md" />
      </main>
    );
  }

  if (!me.data) return null;

  return (
    <main className="flex min-h-dvh bg-slate-100" dir="rtl">
      {/* سطح المكتب: شريط ثابت */}
      <div className="hidden border-l md:block">
        <ConversationList
          userName={me.data.full_name}
          userRole={me.data.role}
        />
      </div>
      {/* الجوال: درج بمكوّن Sheet يضمن trapping للتركيز وإغلاق بمفتاح Escape */}
      <Sheet
        open={isSidebarOpen}
        onOpenChange={(open) => {
          if (!open) closeSidebar();
        }}
      >
        <SheetContent
          side="right"
          className="w-72 gap-0 p-0 md:hidden"
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
      <div className="flex min-w-0 flex-1 justify-center p-4 sm:p-8">{children}</div>
    </main>
  );
}
