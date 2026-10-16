"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function MessageInput({
  disabled,
  onSend,
}: {
  disabled: boolean;
  onSend: (content: string) => void;
}) {
  const [value, setValue] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = value.trim();
    if (!content) return;
    setValue("");
    onSend(content);
  }

  return (
    <form className="flex gap-3 p-6" onSubmit={handleSubmit}>
      <Input
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder="اكتب رسالتك..."
        disabled={disabled}
        className="min-w-0 flex-1"
      />
      <Button type="submit" disabled={disabled || !value.trim()}>
        إرسال
      </Button>
    </form>
  );
}
