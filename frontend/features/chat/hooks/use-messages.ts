"use client";

import { useInfiniteQuery } from "@tanstack/react-query";
import { listMessagesRequest, type Page, type ChatMessage } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";

// ─── رسائل محادثة بالمؤشر التسلسلي (الأحدث يُعرض أسفل) ───
export function useMessages(conversationId: string, limit = 50) {
  return useInfiniteQuery<Page<ChatMessage>>({
    queryKey: [...queryKeys.messages(conversationId), limit],
    queryFn: ({ pageParam }) =>
      listMessagesRequest(conversationId, {
        limit,
        cursor: (pageParam as string | null) ?? null,
      }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
  });
}
