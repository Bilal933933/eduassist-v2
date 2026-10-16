"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { useMe } from "@/features/auth/hooks/use-auth";
import { HomeHero } from "@/features/home/components/home-hero";

export default function Home() {
  const router = useRouter();
  const me = useMe();

  useEffect(() => {
    if (me.data) router.replace("/chat");
  }, [me.data, router]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 p-6" dir="rtl">
      {me.isPending ? (
        <Skeleton className="h-64 w-full max-w-xl" />
      ) : (
        <HomeHero userName={me.data?.full_name} />
      )}
    </main>
  );
}
