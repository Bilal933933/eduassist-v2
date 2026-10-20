import Link from "next/link";
import { RegisterForm } from "@/features/auth/components/register-form";

export default function RegisterPage() {
  return (
    <main className="flex min-h-dvh items-center justify-center bg-slate-950 p-6" dir="rtl">
      <section className="flex w-full max-w-md flex-col items-center gap-6">
        <div className="text-center">
          <p className="mb-2 text-sm font-semibold text-emerald-400">EduAssist V2</p>
          <h1 className="text-balance text-3xl font-bold text-white">حساب جديد</h1>
        </div>
        <RegisterForm />
        <p className="text-sm text-slate-400">
          لديك حساب بالفعل؟{" "}
          <Link href="/login" className="font-semibold text-emerald-400">
            سجّل الدخول
          </Link>
        </p>
      </section>
    </main>
  );
}
