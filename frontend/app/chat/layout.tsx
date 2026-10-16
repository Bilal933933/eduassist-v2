"use client";

import { Menu, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useMe } from "@/features/auth/hooks/use-auth";
import { ConversationList } from "@/features/conversations/components/conversation-list";

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const me = useMe();
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    if (!me.isPending && !me.data) router.replace("/login");
  }, [me.isPending, me.data, router]);

  if (me.isPending) {
    return (
      <main className="flex min-h-screen items-center justify-center" dir="rtl">
        <Skeleton className="h-64 w-full max-w-md" />
      </main>
    );
  }

  if (!me.data) return null;

  return (
    <main className="flex min-h-screen bg-slate-100" dir="rtl">
      {/* سطح المكتب: شريط ثابت */}
      <div className="hidden border-l md:block">
        <ConversationList userName={me.data.full_name} />
      </div>
      {/* الجوال: زر قائمة + درج منزلق */}
      <Button
        size="icon"
        variant="outline"
        className="fixed bottom-6 right-6 z-40 md:hidden"
        onClick={() => setDrawerOpen((open) => !open)}
        aria-label={drawerOpen ? "إغلاق القائمة" : "فتح القائمة"}
      >
        {drawerOpen ? <X className="size-5" /> : <Menu className="size-5" />}
      </Button>
      {drawerOpen && (
        <div className="fixed inset-0 z-30 md:hidden">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setDrawerOpen(false)}
          />
          <div className="absolute inset-y-0 right-0 border-l shadow-xl">
            <ConversationList
              userName={me.data.full_name}
              onSelect={() => setDrawerOpen(false)}
            />
          </div>
        </div>
      )}
      <div className="flex min-w-0 flex-1 justify-center p-4 sm:p-8">{children}</div>
    </main>
  );
}
