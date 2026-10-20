"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { useMe } from "@/features/auth/hooks/use-auth";
import { ProfileForm } from "@/features/profile/components/profile-form";
import { useTeacherProfile } from "@/features/profile/hooks/use-teacher-profile";

export default function ProfilePage() {
  const router = useRouter();
  const me = useMe();
  const profile = useTeacherProfile();

  useEffect(() => {
    if (!me.isPending && !me.data) router.replace("/login");
  }, [me.isPending, me.data, router]);

  if (me.isPending) {
    return (
      <main className="flex min-h-dvh items-center justify-center" dir="rtl">
        <Skeleton className="h-64 w-full max-w-md" />
      </main>
    );
  }

  if (!me.data) return null;

  if (me.data.role !== "teacher") {
    return (
      <main className="flex min-h-dvh items-center justify-center p-4" dir="rtl">
        <section className="w-full max-w-lg rounded-3xl border bg-white p-8 text-center shadow-xl">
          <h1 className="text-lg font-bold text-slate-900">بروفايل المعلم</h1>
          <p className="mt-2 text-sm text-slate-500">
            هذه الصفحة للمعلمين فقط.
          </p>
        </section>
      </main>
    );
  }

  return (
    <main className="flex min-h-dvh items-center justify-center bg-slate-100 p-4" dir="rtl">
      <section className="w-full max-w-lg rounded-3xl border bg-white p-8 shadow-xl">
        <h1 className="text-lg font-bold text-slate-900">بروفايل المعلم</h1>
        <p className="mt-1 text-sm leading-6 text-slate-500">
          المادة والصف يدخلان في تحضير الدرس، فيحصل على خطة مطابقة لمستويات
          طلابك.
        </p>
        <ProfileForm
          key={profile.isPending ? "pending" : "loaded"}
          initial={profile.data ?? null}
        />
      </section>
    </main>
  );
}
