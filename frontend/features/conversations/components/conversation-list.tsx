"use client";

import { LogOut, Plus, Sparkles, UserCog } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { RequestFailedError } from "@/lib/api";
import { useLogout } from "@/features/auth/hooks/use-auth";
import { useConversations, useCreateConversation } from "../hooks/use-conversations";

function formatDate(value: string) {
  const date = new Date(value);
  const today = new Date();
  const sameDay = date.toDateString() === today.toDateString();
  if (sameDay) {
    return date.toLocaleTimeString("ar", { hour: "2-digit", minute: "2-digit" });
  }
  return date.toLocaleDateString("ar", { day: "numeric", month: "short" });
}

export function ConversationList({
  userName,
  userRole,
  onSelect,
  className,
}: {
  userName: string;
  userRole?: string;
  onSelect?: () => void;
  className?: string;
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
    <div className={`flex h-full w-72 flex-col bg-slate-50/50 ${className ?? ""}`}>
      <div className="flex items-center justify-between gap-2 p-4">
        <div className="min-w-0">
          <p className="truncate font-bold text-slate-900">المساعد النحوي</p>
          <p className="truncate text-xs text-slate-500">مرحبًا، {userName}</p>
        </div>
        <Button size="sm" onClick={handleNew} disabled={createConversation.isPending} className="rounded-xl shadow-none">
          <Plus className="size-4" />
          جديد
        </Button>
      </div>
      <div className="h-px bg-slate-200/50" />
      <ScrollArea className="flex-1 px-2 py-2">
        {list.isPending &&
          Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="mb-2 h-14 w-full rounded-2xl" />
          ))}
        {list.isError && (
          <div className="p-4 text-center">
            <p className="text-sm text-red-700">تعذر تحميل المحادثات.</p>
            <Button
              variant="outline"
              size="sm"
              className="mt-3 rounded-xl"
              onClick={() => list.refetch()}
            >
              إعادة المحاولة
            </Button>
          </div>
        )}
        {!list.isPending && !list.isError && items.length === 0 && (
          <div className="px-4 py-10 text-center">
            <div className="mx-auto flex size-10 items-center justify-center rounded-2xl bg-slate-100 text-slate-500">
              <Sparkles className="size-5" />
            </div>
            <p className="mt-3 text-sm font-semibold text-slate-700">
              لا محادثات بعد
            </p>
            <p className="mt-1 text-xs leading-5 text-slate-500">
              ابدأ محادثة جديدة لتسأل عن أي قاعدة نحوية.
            </p>
            <Button size="sm" className="mt-4 rounded-xl" onClick={handleNew}>
              <Plus className="size-4" />
              محادثة جديدة
            </Button>
          </div>
        )}
        {items.map((conversation) => {
          const active = pathname === `/chat/${conversation.id}`;
          return (
            <Link
              key={conversation.id}
              href={`/chat/${conversation.id}`}
              onClick={onSelect}
              aria-current={active ? "page" : undefined}
              className={`mb-1 block rounded-2xl px-3 py-2.5 text-sm transition-all ${
                active
                  ? "bg-emerald-50/80 font-semibold text-emerald-900 shadow-sm"
                  : "text-slate-600 hover:bg-slate-200/50 hover:text-slate-900"
              }`}
            >
              <span className="flex items-center justify-between gap-2">
                <span className="truncate">
                  {conversation.title ?? "محادثة بلا عنوان"}
                </span>
                {conversation.status !== "active" && (
                  <Badge variant="secondary" className="text-[10px]">مؤرشفة</Badge>
                )}
              </span>
              <span className="mt-1 block text-xs tabular-nums text-slate-400">
                {formatDate(conversation.updated_at)}
              </span>
            </Link>
          );
        })}
        {list.hasNextPage && (
          <Button
            variant="ghost"
            size="sm"
            className="mt-2 w-full rounded-xl"
            onClick={() => list.fetchNextPage()}
            disabled={list.isFetchingNextPage}
          >
            {list.isFetchingNextPage ? "جارٍ التحميل..." : "عرض الأقدم"}
          </Button>
        )}
      </ScrollArea>
      <div className="h-px bg-slate-200/50" />
      <div className="space-y-2 p-3">
        {userRole === "teacher" && (
          <Link
            href="/profile"
            onClick={onSelect}
            className={buttonVariants({ variant: "ghost", size: "sm", className: "w-full justify-start rounded-xl text-slate-600 hover:bg-slate-200/50" })}
          >
            <UserCog className="size-4 ml-2" />
            بروفايل المعلم
          </Link>
        )}
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start rounded-xl text-slate-600 hover:bg-red-50 hover:text-red-600"
          onClick={handleLogout}
          disabled={logout.isPending}
        >
          <LogOut className="size-4 ml-2" />
          تسجيل الخروج
        </Button>
      </div>
    </div>
  );
}
