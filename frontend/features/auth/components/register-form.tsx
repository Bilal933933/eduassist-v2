"use client";

import { Eye, EyeOff } from "lucide-react";
import { FormEvent, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RequestFailedError } from "@/lib/api";
import { useRegister } from "../hooks/use-auth";

export function RegisterForm() {
  const register = useRegister();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [role, setRole] = useState<"teacher" | "student">("teacher");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await register.mutateAsync({
        full_name: fullName.trim(),
        email: email.trim(),
        password,
        role,
      });
    } catch (error) {
      toast.error(
        error instanceof RequestFailedError ? error.message : "تعذر إنشاء الحساب.",
      );
    }
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>حساب جديد</CardTitle>
        <CardDescription>أنشئ حساب مدرس أو طالب لبدء محادثاتك المحفوظة.</CardDescription>
      </CardHeader>
      <CardContent>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-1.5">
            <Label htmlFor="register-name">الاسم الكامل</Label>
            <Input
              id="register-name"
              placeholder="مثال: أحمد محمد"
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              autoComplete="name"
              minLength={2}
              required
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="register-email">البريد الإلكتروني</Label>
            <Input
              id="register-email"
              type="email"
              placeholder="name@example.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              required
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="register-password">كلمة المرور</Label>
            <div className="relative">
              <Input
                id="register-password"
                type={showPassword ? "text" : "password"}
                placeholder="8 أحرف فأكثر"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="new-password"
                className="pl-10"
                minLength={8}
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword((shown) => !shown)}
                aria-label={showPassword ? "إخفاء كلمة المرور" : "إظهار كلمة المرور"}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700"
              >
                {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
              </button>
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>الدور</Label>
            <div className="grid grid-cols-2 gap-2">
              {(["teacher", "student"] as const).map((option) => (
                <Button
                  key={option}
                  type="button"
                  variant={role === option ? "default" : "outline"}
                  onClick={() => setRole(option)}
                >
                  {option === "teacher" ? "مدرس" : "طالب"}
                </Button>
              ))}
            </div>
          </div>
          <Button className="w-full" type="submit" disabled={register.isPending}>
            {register.isPending ? "جارٍ الإنشاء..." : "إنشاء الحساب"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
