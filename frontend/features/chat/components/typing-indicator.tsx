"use client";

export function TypingIndicator() {
  return (
    <div className="flex w-full flex-col items-end gap-1" aria-live="polite">
      <div className="max-w-[85%] rounded-2xl border border-border bg-background px-4 py-3 shadow-sm">
        <span className="flex items-center gap-1.5" aria-label="يفكر المساعد">
          {[0, 1, 2].map((dot) => (
            <span
              key={dot}
              className="size-1.5 animate-bounce rounded-full bg-muted-foreground/60 motion-reduce:animate-none"
              style={{ animationDelay: `${dot * 150}ms` }}
            />
          ))}
        </span>
      </div>
    </div>
  );
}
