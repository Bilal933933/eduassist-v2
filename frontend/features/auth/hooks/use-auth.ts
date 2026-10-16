"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import {
  loginRequest,
  logoutRequest,
  meRequest,
  registerRequest,
} from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";

// ─── الجلسة الحالية (لا تُعيد المحاولة عند 401) ───
export function useMe() {
  return useQuery({
    queryKey: queryKeys.me,
    queryFn: meRequest,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
}

function useInvalidateSession() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.me });
    queryClient.invalidateQueries({ queryKey: queryKeys.conversations });
  };
}

// ─── الدخول: نجاح ← إبطال الجلسة ← الذهاب للدردشة ───
export function useLogin() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const invalidate = useInvalidateSession();

  return useMutation({
    mutationFn: loginRequest,
    onSuccess: (user) => {
      queryClient.setQueryData(queryKeys.me, user);
      invalidate();
      router.replace("/chat");
    },
  });
}

// ─── التسجيل: نفس مسار الدخول بعد الإنشاء ───
export function useRegister() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const invalidate = useInvalidateSession();

  return useMutation({
    mutationFn: registerRequest,
    onSuccess: (user) => {
      queryClient.setQueryData(queryKeys.me, user);
      invalidate();
      router.replace("/chat");
    },
  });
}

// ─── الخروج: مسح الكاش المحلي والعودة للدخول ───
export function useLogout() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: logoutRequest,
    onSettled: () => {
      queryClient.clear();
      router.replace("/login");
    },
  });
}
