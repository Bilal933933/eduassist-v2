"use client";

const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:5002"
).replace(/\/$/, "");

// ─── أنواع العقد الموحد ───
export type ApiError = {
  code: string;
  message: string;
  details?: unknown;
};

type Envelope<T> = {
  success: boolean;
  data?: T;
  error?: ApiError;
};

export class RequestFailedError extends Error {
  code: string;
  details?: unknown;

  constructor(error: ApiError) {
    super(error.message);
    this.code = error.code;
    this.details = error.details;
  }
}

// ─── أنواع المجال ───
export type User = {
  id: string;
  full_name: string;
  email: string;
  role: string;
};

export type Conversation = {
  id: string;
  user_id: string;
  title: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type ChatMessage = {
  id: string;
  conversation_id: string;
  user_id: string;
  sender: "user" | "assistant";
  content: string;
  sequence_number: number;
  created_at: string;
};

export type Page<T> = {
  items: T[];
  next_cursor: string | null;
};

async function request<T>(path: string, options: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  const body = (await response.json()) as Envelope<T>;
  if (!response.ok || !body.success || body.data === undefined) {
    throw new RequestFailedError(
      body.error ?? { code: `HTTP_${response.status}`, message: "تعذر إكمال الطلب." },
    );
  }
  return body.data;
}

function post<T>(path: string, payload?: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    body: payload === undefined ? undefined : JSON.stringify(payload),
  });
}

// ─── المصادقة ───
export function loginRequest(payload: { email: string; password: string }) {
  return post<User>("/api/auth/login", payload);
}

export function registerRequest(payload: {
  full_name: string;
  email: string;
  password: string;
  role: "teacher" | "student";
}) {
  return post<User>("/api/auth/register", payload);
}

export function logoutRequest() {
  return post<{ logged_out: boolean }>("/api/auth/logout");
}

export function meRequest() {
  return request<User>("/api/auth/me", { method: "GET" });
}

// ─── المحادثات ───
export function createConversationRequest(title?: string) {
  return post<Conversation>("/api/conversations", { title: title ?? null });
}

export function listConversationsRequest(params: {
  limit?: number;
  cursor?: string | null;
}) {
  const query = new URLSearchParams();
  if (params.limit !== undefined) query.set("limit", String(params.limit));
  if (params.cursor) query.set("cursor", params.cursor);
  const suffix = query.toString();
  return request<Page<Conversation>>(
    `/api/conversations${suffix ? `?${suffix}` : ""}`,
    { method: "GET" },
  );
}

export function listMessagesRequest(
  conversationId: string,
  params: { limit?: number; cursor?: string | null },
) {
  const query = new URLSearchParams();
  if (params.limit !== undefined) query.set("limit", String(params.limit));
  if (params.cursor) query.set("cursor", params.cursor);
  const suffix = query.toString();
  return request<Page<ChatMessage>>(
    `/api/conversations/${conversationId}/messages${suffix ? `?${suffix}` : ""}`,
    { method: "GET" },
  );
}

export function sendMessageRequest(conversationId: string, message: string) {
  return post<{ conversation_id: string; accepted: boolean }>("/api/chat", {
    conversation_id: conversationId,
    message,
  });
}

export function socketUrlFor(conversationId: string) {
  return `${API_URL.replace(/^http/, "ws")}/api/ws/${conversationId}`;
}
