"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getTeacherProfileRequest,
  saveTeacherProfileRequest,
} from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";

// ─── قراءة بروفايل المعلم ───
export function useTeacherProfile() {
  return useQuery({
    queryKey: queryKeys.teacherProfile,
    queryFn: getTeacherProfileRequest,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
}

// ─── حفظ بروفايل المعلم وتحديث الكاش ───
export function useSaveTeacherProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: saveTeacherProfileRequest,
    onSuccess: (profile) => {
      queryClient.setQueryData(queryKeys.teacherProfile, profile);
    },
  });
}
