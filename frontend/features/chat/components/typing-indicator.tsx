"use client";

export function TypingIndicator() {
  return (
    <p className="flex items-center gap-1 text-sm text-slate-400" aria-live="polite">
      يفكر المساعد
      {[0, 1, 2].map((dot) => (
        <span
          key={dot}
          className="size-1.5 animate-bounce rounded-full bg-slate-400"
          style={{ animationDelay: `${dot * 150}ms` }}
        />
      ))}
    </p>
  );
}
