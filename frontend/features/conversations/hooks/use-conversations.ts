"use client";

import { useInfiniteQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { usePathname, useRouter } from "next/navigation";
import {
  createConversationRequest,
  deleteConversationRequest,
  listConversationsRequest,
  RequestFailedError,
  type Conversation,
  type Page,
} from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";

// ─── القائمة بالمؤشر: زر "عرض الأقدم" يطلب التالي ───
export function useConversations(limit = 50) {
  return useInfiniteQuery<Page<Conversation>>({
    queryKey: [...queryKeys.conversations, limit],
    queryFn: ({ pageParam }) =>
      listConversationsRequest({
        limit,
        cursor: (pageParam as string | null) ?? null,
      }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
  });
}

// ─── محادثة واحدة من الكاش (للعنوان دون طلب جديد) ───
export function useConversation(conversationId: string) {
  const list = useConversations();
  const conversation = list.data?.pages
    .flatMap((page) => page.items)
    .find((item) => item.id === conversationId);
  return { conversation, isPending: list.isPending };
}

// ─── الإنشاء: نجاح ← إبطال القائمة ← فتح المحادثة ───
export function useCreateConversation() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (title?: string) => createConversationRequest(title),
    onSuccess: (conversation) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.conversations });
      router.replace(`/chat/${conversation.id}`);
    },
  });
}

// ─── الحذف: 404 يعني محادثة محذوفة مسبقًا ← نجاح ───
export function useDeleteConversation() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const pathname = usePathname();

  return useMutation({
    mutationFn: async (conversationId: string) => {
      try {
        return await deleteConversationRequest(conversationId);
      } catch (error) {
        const alreadyGone =
          error instanceof RequestFailedError &&
          (error.code === "HTTP_404" || error.code === "CONVERSATION_NOT_FOUND");
        if (alreadyGone) return { deleted: true };
        throw error;
      }
    },
    onSuccess: (_, conversationId) => {
      // الحذف يقتصر على النسخ غير المعروضة: إزالة استعلام نشط تُطلق جلبًا
      // لمحادثة محذوفة فيصل 404 بلا فائدة. المفتوح يُغادر ثم يُجمع تلقائيًا.
      queryClient.removeQueries({
        queryKey: queryKeys.messages(conversationId),
        type: "inactive",
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.conversations });
      if (pathname === `/chat/${conversationId}`) {
        router.replace("/chat/new");
      }
    },
  });
}
