"use client";

import { useState } from "react";
import { LogOut, Plus, Sparkles, Trash2, UserCog } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { toast } from "sonner";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { RequestFailedError, type Conversation } from "@/lib/api";
import { useLogout } from "@/features/auth/hooks/use-auth";
import {
  useConversations,
  useCreateConversation,
  useDeleteConversation,
} from "../hooks/use-conversations";

function formatDate(value: string) {
  const date = new Date(value);
  const today = new Date();
  const sameDay = date.toDateString() === today.toDateString();
  if (sameDay) {
    return date.toLocaleTimeString("ar", { hour: "2-digit", minute: "2-digit" });
  }
  return date.toLocaleDateString("ar", { day: "numeric", month: "short" });
}

// ─── صف واحد: رابط المحادثة وزر الحذف شقيقان لا متداخلان ───
function ConversationRow({
  conversation,
  active,
  onSelect,
}: {
  conversation: Conversation;
  active: boolean;
  onSelect?: () => void;
}) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const deleteConversation = useDeleteConversation();
  const title = conversation.title ?? "محادثة بلا عنوان";
  const isDeleting =
    deleteConversation.isPending &&
    deleteConversation.variables === conversation.id;

  async function handleDelete() {
    try {
      await deleteConversation.mutateAsync(conversation.id);
      toast.success("تم حذف المحادثة.");
      onSelect?.();
    } catch (error) {
      toast.error(
        error instanceof RequestFailedError ? error.message : "تعذر حذف المحادثة.",
      );
    } finally {
      setConfirmOpen(false);
    }
  }

  return (
    <div
      className={`group mb-1 flex items-center gap-1 rounded-2xl transition-all ${
        active
          ? "bg-emerald-50/80 font-semibold text-emerald-900 shadow-sm dark:bg-emerald-500/10 dark:text-emerald-100"
          : "text-muted-foreground hover:bg-accent hover:text-foreground"
      }`}
    >
      <Link
        href={`/chat/${conversation.id}`}
        onClick={onSelect}
        aria-current={active ? "page" : undefined}
        className="flex min-w-0 flex-1 items-center justify-between gap-2 rounded-2xl px-3 py-2.5 text-sm"
      >
        <span className="min-w-0 flex-1 truncate">{title}</span>
        {conversation.status !== "active" && (
          <Badge variant="secondary" className="shrink-0 text-[10px]">
            مؤرشفة
          </Badge>
        )}
        <span className="shrink-0 text-[11px] tabular-nums text-muted-foreground/80">
          {formatDate(conversation.updated_at)}
        </span>
      </Link>
      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogTrigger
          render={
            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label={`حذف ${title}`}
              className="size-8 shrink-0 rounded-xl text-muted-foreground transition-opacity hover:bg-red-50 hover:text-red-600 focus-visible:opacity-100 dark:hover:bg-red-500/10 dark:hover:text-red-400 md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100"
            />
          }
        >
          <Trash2 className="size-4" />
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>حذف المحادثة؟</AlertDialogTitle>
            <AlertDialogDescription>
              سيُحذف سجل المحادثة ورسائلها نهائيًا، ولا يمكن التراجع.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>إلغاء</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={handleDelete}
              disabled={isDeleting}
            >
              {isDeleting ? "جارٍ الحذف..." : "حذف"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
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
    <div className={`flex h-full w-72 flex-col bg-muted/40 ${className ?? ""}`}>
      <div className="flex items-center justify-between gap-2 p-4">
        <div className="min-w-0">
          <p className="truncate font-bold text-foreground">المساعد النحوي</p>
          <p className="truncate text-xs text-muted-foreground">مرحبًا، {userName}</p>
        </div>
        <Button size="sm" onClick={handleNew} disabled={createConversation.isPending} className="rounded-xl shadow-none">
          <Plus className="size-4" />
          جديد
        </Button>
      </div>
      <div className="h-px bg-accent" />
      <ScrollArea className="flex-1 px-2 py-2">
        {list.isPending &&
          Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="mb-2 h-14 w-full rounded-2xl" />
          ))}
        {list.isError && (
          <div className="p-4 text-center">
            <p className="text-sm text-red-700 dark:text-red-400">تعذر تحميل المحادثات.</p>
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
            <div className="mx-auto flex size-10 items-center justify-center rounded-2xl bg-muted text-muted-foreground">
              <Sparkles className="size-5" />
            </div>
            <p className="mt-3 text-sm font-semibold text-foreground/90">
              لا محادثات بعد
            </p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              ابدأ محادثة جديدة لتسأل عن أي قاعدة نحوية.
            </p>
            <Button size="sm" className="mt-4 rounded-xl" onClick={handleNew}>
              <Plus className="size-4" />
              محادثة جديدة
            </Button>
          </div>
        )}
        {items.map((conversation) => (
          <ConversationRow
            key={conversation.id}
            conversation={conversation}
            active={pathname === `/chat/${conversation.id}`}
            onSelect={onSelect}
          />
        ))}
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
      <div className="h-px bg-accent" />
      <div className="space-y-2 p-3">
        {userRole === "teacher" && (
          <Link
            href="/profile"
            onClick={onSelect}
            className={buttonVariants({ variant: "ghost", size: "sm", className: "w-full justify-start rounded-xl text-muted-foreground hover:bg-accent" })}
          >
            <UserCog className="size-4 ml-2" />
            بروفايل المعلم
          </Link>
        )}
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start rounded-xl text-muted-foreground hover:bg-red-50 dark:hover:bg-red-500/10 hover:text-red-600 dark:hover:text-red-400"
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
