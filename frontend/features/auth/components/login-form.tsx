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
import { useLogin } from "../hooks/use-auth";

export function LoginForm() {
  const login = useLogin();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await login.mutateAsync({ email: email.trim(), password });
    } catch (error) {
      toast.error(
        error instanceof RequestFailedError ? error.message : "تعذر تسجيل الدخول.",
      );
    }
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>تسجيل الدخول</CardTitle>
        <CardDescription>ادخل ببريدك وكلمة مرورك لمتابعة محادثاتك.</CardDescription>
      </CardHeader>
      <CardContent>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-1.5">
            <Label htmlFor="login-email">البريد الإلكتروني</Label>
            <Input
              id="login-email"
              type="email"
              placeholder="name@example.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              required
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="login-password">كلمة المرور</Label>
            <div className="relative">
              <Input
                id="login-password"
                type={showPassword ? "text" : "password"}
                placeholder="••••••••"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                className="pl-10"
                minLength={1}
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword((shown) => !shown)}
                aria-label={showPassword ? "إخفاء كلمة المرور" : "إظهار كلمة المرور"}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground/80 hover:text-foreground/90"
              >
                {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
              </button>
            </div>
          </div>
          <Button className="w-full" type="submit" disabled={login.isPending}>
            {login.isPending ? "جارٍ الدخول..." : "دخول"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
