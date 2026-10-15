"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

type User = {
  id: string;
  full_name: string;
  email: string;
  role: string;
};

type Message = {
  sender: "user" | "assistant";
  content: string;
};

type ApiEnvelope<T> = {
  success: boolean;
  data?: T;
  error?: { message?: string };
};

type ChatEvent = {
  type: "chat.started" | "chat.completed" | "chat.failed";
  data: { response?: string } | null;
  error: { message?: string } | null;
};

const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:5002"
).replace(/\/$/, "");

async function request<T>(path: string, options: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  const body = (await response.json()) as ApiEnvelope<T>;
  if (!response.ok || !body.success || body.data === undefined) {
    throw new Error(body.error?.message ?? "تعذر إكمال الطلب.");
  }
  return body.data;
}

export default function Home() {
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [user, setUser] = useState<User | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isBusy, setIsBusy] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!conversationId) return;

    const socketUrl = API_URL.replace(/^http/, "ws");
    const socket = new WebSocket(`${socketUrl}/api/ws/${conversationId}`);
    socketRef.current = socket;
    socket.onopen = () => setIsConnected(true);
    socket.onclose = () => setIsConnected(false);
    socket.onerror = () => setError("تعذر فتح قناة المحادثة اللحظية.");
    socket.onmessage = (event) => {
      const chatEvent = JSON.parse(event.data) as ChatEvent;
      if (chatEvent.type === "chat.completed" && chatEvent.data?.response) {
        setMessages((current) => [
          ...current,
          { sender: "assistant", content: chatEvent.data?.response ?? "" },
        ]);
        setIsBusy(false);
      }
      if (chatEvent.type === "chat.failed") {
        setError(chatEvent.error?.message ?? "تعذر إكمال المحادثة.");
        setIsBusy(false);
      }
    };

    return () => {
      socket.close();
      socketRef.current = null;
    };
  }, [conversationId]);

  async function handleAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsBusy(true);
    const form = new FormData(event.currentTarget);
    const payload =
      authMode === "register"
        ? {
            full_name: form.get("full_name"),
            email: form.get("email"),
            password: form.get("password"),
            role: "teacher",
          }
        : {
            email: form.get("email"),
            password: form.get("password"),
          };

    try {
      const authenticatedUser = await request<User>(`/api/auth/${authMode}`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      const conversation = await request<{ id: string }>("/api/conversations", {
        method: "POST",
        body: JSON.stringify({ title: "تجربة المساعد" }),
      });
      setUser(authenticatedUser);
      setConversationId(conversation.id);
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : "حدث خطأ غير متوقع.",
      );
    } finally {
      setIsBusy(false);
    }
  }

  async function handleSend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = message.trim();
    if (!content || !conversationId || !isConnected || isBusy) return;

    setMessage("");
    setError("");
    setIsBusy(true);
    setMessages((current) => [...current, { sender: "user", content }]);
    try {
      await request<{ accepted: boolean }>("/api/chat", {
        method: "POST",
        body: JSON.stringify({ conversation_id: conversationId, message: content }),
      });
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : "تعذر إرسال الرسالة.",
      );
      setIsBusy(false);
    }
  }

  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 p-6" dir="rtl">
        <section className="w-full max-w-md rounded-3xl border border-white/10 bg-white p-8 shadow-2xl">
          <p className="mb-2 text-sm font-semibold text-emerald-700">EduAssist V2</p>
          <h1 className="text-3xl font-bold text-slate-950">جرّب المساعد النحوي</h1>
          <p className="mt-2 text-sm text-slate-500">سجّل الدخول لبدء محادثة حقيقية مع النموذج.</p>

          <div className="mt-6 grid grid-cols-2 rounded-xl bg-slate-100 p-1 text-sm">
            {(["login", "register"] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setAuthMode(mode)}
                className={`rounded-lg px-3 py-2 font-medium ${authMode === mode ? "bg-white text-slate-950 shadow-sm" : "text-slate-500"}`}
              >
                {mode === "login" ? "تسجيل الدخول" : "حساب جديد"}
              </button>
            ))}
          </div>

          <form className="mt-6 space-y-4" onSubmit={handleAuth}>
            {authMode === "register" && (
              <input className="w-full rounded-xl border px-4 py-3" name="full_name" placeholder="الاسم الكامل" minLength={2} required />
            )}
            <input className="w-full rounded-xl border px-4 py-3" name="email" type="email" placeholder="البريد الإلكتروني" required />
            <input className="w-full rounded-xl border px-4 py-3" name="password" type="password" placeholder="كلمة المرور" minLength={authMode === "register" ? 8 : 1} required />
            {error && <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}
            <button disabled={isBusy} className="w-full rounded-xl bg-emerald-700 px-4 py-3 font-semibold text-white disabled:opacity-50">
              {isBusy ? "جارٍ الاتصال..." : authMode === "login" ? "دخول" : "إنشاء الحساب"}
            </button>
          </form>
        </section>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen justify-center bg-slate-100 p-4 sm:p-8" dir="rtl">
      <section className="flex w-full max-w-4xl flex-col overflow-hidden rounded-3xl border bg-white shadow-xl">
        <header className="flex items-center justify-between border-b px-6 py-4">
          <div>
            <h1 className="font-bold text-slate-950">المساعد النحوي</h1>
            <p className="text-sm text-slate-500">مرحبًا، {user.full_name}</p>
          </div>
          <span className={`rounded-full px-3 py-1 text-xs font-medium ${isConnected ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>
            {isConnected ? "متصل" : "جارٍ الاتصال"}
          </span>
        </header>

        <div className="min-h-[60vh] flex-1 space-y-4 overflow-y-auto bg-slate-50 p-6">
          {messages.length === 0 && (
            <div className="mx-auto mt-20 max-w-md text-center text-slate-500">
              <p className="text-lg font-semibold text-slate-700">ابدأ بسؤال بسيط</p>
              <p className="mt-2 text-sm">مثال: اشرح لي الفرق بين الفاعل ونائب الفاعل.</p>
            </div>
          )}
          {messages.map((item, index) => (
            <div key={`${item.sender}-${index}`} className={`flex ${item.sender === "user" ? "justify-start" : "justify-end"}`}>
              <p className={`max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-7 ${item.sender === "user" ? "bg-emerald-700 text-white" : "border bg-white text-slate-800"}`}>
                {item.content}
              </p>
            </div>
          ))}
          {isBusy && <p className="text-sm text-slate-400">يفكر المساعد...</p>}
        </div>

        {error && <p className="mx-6 mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        <form className="flex gap-3 p-6" onSubmit={handleSend}>
          <input
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            className="min-w-0 flex-1 rounded-xl border px-4 py-3"
            placeholder="اكتب رسالتك..."
            disabled={!isConnected || isBusy}
          />
          <button disabled={!isConnected || isBusy || !message.trim()} className="rounded-xl bg-emerald-700 px-6 py-3 font-semibold text-white disabled:opacity-40">
            إرسال
          </button>
        </form>
      </section>
    </main>
  );
}
