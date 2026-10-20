"use client";

import { FormEvent, KeyboardEvent, useState } from "react";
import { Send, Paperclip, Mic } from "lucide-react";
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
    <form className="p-4 pb-8 sm:px-6" onSubmit={handleSubmit}>
      <div className="mx-auto flex max-w-3xl flex-col rounded-3xl border border-slate-200 bg-white shadow-2xl transition-all focus-within:border-emerald-500 focus-within:ring-2 focus-within:ring-emerald-500/20">
        <Textarea
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={isBlocked}
          rows={2}
          aria-label="نص الرسالة"
          className="max-h-40 min-h-12 w-full resize-none border-0 bg-transparent px-4 pt-3.5 pb-2 text-slate-800 shadow-none focus-visible:ring-0"
        />
        <div className="flex items-center justify-between px-3 pb-3 pt-1">
          <div className="flex items-center gap-1 text-slate-400">
            <Button
              type="button"
              size="icon"
              variant="ghost"
              disabled={isBlocked}
              aria-label="إرفاق ملف"
              className="size-9 rounded-full hover:bg-slate-100 hover:text-slate-600"
              onClick={() => {}}
            >
              <Paperclip className="size-4" />
            </Button>
            <Button
              type="button"
              size="icon"
              variant="ghost"
              disabled={isBlocked}
              aria-label="تسجيل صوتي"
              className="size-9 rounded-full hover:bg-slate-100 hover:text-slate-600"
              onClick={() => {}}
            >
              <Mic className="size-4" />
            </Button>
          </div>
          <div className="flex items-center gap-2">
            <span className="hidden text-[11px] text-slate-400 sm:inline">
              {disabledReason ?? "Enter للإرسال"}
            </span>
            <Button
              type="submit"
              size="icon"
              disabled={isBlocked || !value.trim()}
              aria-label="إرسال الرسالة"
              className="size-9 rounded-full bg-emerald-700 text-white transition-all hover:bg-emerald-800 disabled:opacity-40"
            >
              <Send className="size-4 rotate-180" />
            </Button>
          </div>
        </div>
      </div>
      <p className="mx-auto mt-2 max-w-3xl text-center text-[11px] text-slate-400 sm:hidden">
        {disabledReason ?? "Enter للإرسال"}
      </p>
    </form>
  );
}
