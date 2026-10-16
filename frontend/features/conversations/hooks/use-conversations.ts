"use client";

import { useInfiniteQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import {
  createConversationRequest,
  listConversationsRequest,
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
