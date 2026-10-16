"use client";

import { LogOut, Plus } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { RequestFailedError } from "@/lib/api";
import { useLogout } from "@/features/auth/hooks/use-auth";
import { useConversations, useCreateConversation } from "../hooks/use-conversations";

function formatDate(value: string) {
  return new Date(value).toLocaleDateString("ar", {
    day: "numeric",
    month: "short",
  });
}

export function ConversationList({
  userName,
  onSelect,
}: {
  userName: string;
  onSelect?: () => void;
}) {
  const pathname = usePathname();
  const logout = useLogout();
  const createConversation = useCreateConversation();
  const list = useConversations();

  async function handleLogout() {
    try {
      await logout.mutateAsync();
    } catch {
      toast.error("تعذر تسجيل الخروج.");
    }
  }

  async function handleNew() {
    try {
      await createConversation.mutateAsync("محادثة جديدة");
      onSelect?.();
    } catch (error) {
      toast.error(
        error instanceof RequestFailedError ? error.message : "تعذر إنشاء المحادثة.",
      );
    }
  }

  const items = list.data?.pages.flatMap((page) => page.items) ?? [];

  return (
    <div className="flex h-full w-72 flex-col bg-white">
      <div className="flex items-center justify-between p-4">
        <div>
          <p className="font-bold">المساعد النحوي</p>
          <p className="text-xs text-slate-500">مرحبًا، {userName}</p>
        </div>
        <Button size="sm" onClick={handleNew} disabled={createConversation.isPending}>
          <Plus className="size-4" />
          جديد
        </Button>
      </div>
      <Separator />
      <ScrollArea className="flex-1 px-2 py-2">
        {list.isPending &&
          Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="mb-2 h-14 w-full" />
          ))}
        {list.isError && (
          <p className="p-4 text-sm text-red-700">تعذر تحميل المحادثات.</p>
        )}
        {!list.isPending && items.length === 0 && (
          <p className="p-4 text-center text-sm text-slate-400">
            لا محادثات بعد — ابدأ واحدة جديدة.
          </p>
        )}
        {items.map((conversation) => {
          const active = pathname === `/chat/${conversation.id}`;
          return (
            <Link
              key={conversation.id}
              href={`/chat/${conversation.id}`}
              onClick={onSelect}
              className={`mb-1 block rounded-xl px-3 py-2.5 text-sm transition-colors ${
                active ? "bg-emerald-50 font-semibold" : "hover:bg-slate-100"
              }`}
            >
              <span className="flex items-center justify-between gap-2">
                <span className="truncate">
                  {conversation.title ?? "محادثة بلا عنوان"}
                </span>
                {conversation.status !== "active" && (
                  <Badge variant="secondary">مؤرشفة</Badge>
                )}
              </span>
              <span className="mt-1 block text-xs text-slate-400">
                {formatDate(conversation.updated_at)}
              </span>
            </Link>
          );
        })}
        {list.hasNextPage && (
          <Button
            variant="ghost"
            size="sm"
            className="mt-2 w-full"
            onClick={() => list.fetchNextPage()}
            disabled={list.isFetchingNextPage}
          >
            {list.isFetchingNextPage ? "جارٍ التحميل..." : "عرض الأقدم"}
          </Button>
        )}
      </ScrollArea>
      <Separator />
      <div className="p-4">
        <Button
          variant="outline"
          className="w-full"
          onClick={handleLogout}
          disabled={logout.isPending}
        >
          <LogOut className="size-4" />
          تسجيل الخروج
        </Button>
      </div>
    </div>
  );
}
