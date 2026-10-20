"use client";

// ─── مفاتيح استعلامات TanStack Query الوحيدة (للإبطال المركزي) ───
export const queryKeys = {
  me: ["me"],
  conversations: ["conversations"],
  messages: (conversationId: string) => ["messages", conversationId],
  teacherProfile: ["teacher-profile"],
} as const;
