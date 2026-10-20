"use client";

import { FormEvent, KeyboardEvent, useState } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export function MessageInput({
  disabled,
  disabledReason,
  placeholder = "اكتب رسالتك...",
  onSend,
}: {
  disabled: boolean;
  disabledReason?: string;
  placeholder?: string;
  onSend: (content: string) => Promise<unknown> | void;
}) {
  const [value, setValue] = useState("");
  const [sending, setSending] = useState(false);
  const isBlocked = disabled || sending;

  async function submit(content: string) {
    if (isBlocked) return;
    setSending(true);
    try {
      await onSend(content);
      // لا يُمسح النص إلا بعد قبول الإرسال حتى لا يضيع على المستخدم.
      setValue("");
    } catch {
      // الخطأ يُبلَّغ من طبقة الاستدعاء ويبقى النص كما هو لإعادة الإرسال.
    } finally {
      setSending(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = value.trim();
    if (!content) return;
    void submit(content);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) {
      return;
    }
    event.preventDefault();
    const content = value.trim();
    if (!content) return;
    void submit(content);
  }

  return (
    <form className="border-t bg-white p-3 sm:p-4" onSubmit={handleSubmit}>
      <div className="mx-auto flex max-w-4xl items-end gap-2">
        <div className="relative flex-1">
          <Textarea
            value={value}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={isBlocked}
            rows={1}
            aria-label="نص الرسالة"
            className="max-h-40 min-h-11 resize-none border-slate-200 bg-slate-50 py-3 leading-6 focus-visible:bg-white"
          />
        </div>
        <Button
          type="submit"
          size="icon"
          disabled={isBlocked || !value.trim()}
          aria-label="إرسال الرسالة"
          className="size-11 shrink-0 rounded-xl bg-emerald-700 text-white hover:bg-emerald-800"
        >
          <Send className="size-4 rotate-180" />
        </Button>
      </div>
      <p className="mx-auto mt-1.5 max-w-4xl px-1 text-[11px] text-slate-400">
        {disabledReason ?? "Enter للإرسال · Shift+Enter لسطر جديد"}
      </p>
    </form>
  );
}
