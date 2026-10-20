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
    <div className={`flex h-full w-72 flex-col bg-white ${className ?? ""}`}>
      <div className="flex items-center justify-between gap-2 p-4">
        <div className="min-w-0">
          <p className="truncate font-bold text-slate-900">المساعد النحوي</p>
          <p className="truncate text-xs text-slate-500">مرحبًا، {userName}</p>
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
          <div className="p-4 text-center">
            <p className="text-sm text-red-700">تعذر تحميل المحادثات.</p>
            <Button
              variant="outline"
              size="sm"
              className="mt-3"
              onClick={() => list.refetch()}
            >
              إعادة المحاولة
            </Button>
          </div>
        )}
        {!list.isPending && !list.isError && items.length === 0 && (
          <div className="px-4 py-10 text-center">
            <div className="mx-auto flex size-10 items-center justify-center rounded-xl bg-slate-100 text-slate-500">
              <Sparkles className="size-5" />
            </div>
            <p className="mt-3 text-sm font-semibold text-slate-700">
              لا محادثات بعد
            </p>
            <p className="mt-1 text-xs leading-5 text-slate-500">
              ابدأ محادثة جديدة لتسأل عن أي قاعدة نحوية.
            </p>
            <Button size="sm" className="mt-4" onClick={handleNew}>
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
              className={`mb-1 block rounded-xl px-3 py-2.5 text-sm transition-colors ${
                active
                  ? "bg-emerald-50 font-semibold text-emerald-900"
                  : "text-slate-700 hover:bg-slate-100"
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
            className="mt-2 w-full"
            onClick={() => list.fetchNextPage()}
            disabled={list.isFetchingNextPage}
          >
            {list.isFetchingNextPage ? "جارٍ التحميل..." : "عرض الأقدم"}
          </Button>
        )}
      </ScrollArea>
      <Separator />
      <div className="space-y-2 p-4">
        {userRole === "teacher" && (
          <Link
            href="/profile"
            onClick={onSelect}
            className={buttonVariants({ variant: "outline", className: "w-full" })}
          >
            <UserCog className="size-4" />
            بروفايل المعلم
          </Link>
        )}
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
