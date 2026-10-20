import Link from "next/link";
import { LoginForm } from "@/features/auth/components/login-form";

export default function LoginPage() {
  return (
    <main className="flex min-h-dvh items-center justify-center bg-slate-950 p-6" dir="rtl">
      <section className="flex w-full max-w-md flex-col items-center gap-6">
        <div className="text-center">
          <p className="mb-2 text-sm font-semibold text-emerald-400">EduAssist V2</p>
          <h1 className="text-balance text-3xl font-bold text-white">تسجيل الدخول</h1>
        </div>
        <LoginForm />
        <p className="text-sm text-slate-400">
          ليس لديك حساب؟{" "}
          <Link href="/register" className="font-semibold text-emerald-400">
            أنشئ حسابًا
          </Link>
        </p>
      </section>
    </main>
  );
}
