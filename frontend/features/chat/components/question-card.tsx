"use client";

import { useState } from "react";
import { Check, X } from "lucide-react";
import type { Interaction } from "@/lib/api";
import { Button } from "@/components/ui/button";

type QuestionCardProps = {
  interactionId: string;
  interaction: Interaction;
  disabled?: boolean;
  onAnswer: (
    interactionId: string,
    answers: Record<string, string>,
    message: string,
  ) => Promise<void>;
  onDismiss: (interactionId: string) => Promise<void>;
};

export function QuestionCard({
  interactionId,
  interaction,
  disabled = false,
  onAnswer,
  onDismiss,
}: QuestionCardProps) {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [custom, setCustom] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const errorId = `interaction-${interactionId}-error`;

  if (interaction.status !== "open") {
    const completed = interaction.status === "answered";
    return (
      <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
        {completed ? "تم إرسال إجاباتك." : "تم إغلاق الأسئلة."}
        {completed && interaction.answers && (
          <ul className="mt-2 space-y-1">
            {Object.entries(interaction.answers).map(([slot, value]) => (
              <li key={slot}>
                <span className="font-medium text-slate-800">{slot}:</span>{" "}
                {value}
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  const isDisabled = disabled || submitted;

  function selectOption(slot: string, value: string) {
    setAnswers((current) => ({ ...current, [slot]: value }));
    setCustom((current) => ({ ...current, [slot]: "" }));
    setError("");
  }

  function typeCustom(slot: string, value: string) {
    setCustom((current) => ({ ...current, [slot]: value }));
    setAnswers((current) => ({ ...current, [slot]: value.trim() }));
    setError("");
  }

  async function submit() {
    const missing = interaction.questions.filter(
      (question) => question.required && !answers[question.slot]?.trim(),
    );
    if (missing.length > 0) {
      setError("أكمل الحقول المطلوبة قبل الإرسال.");
      return;
    }
    const clean = Object.fromEntries(
      Object.entries(answers)
        .map(([slot, value]) => [slot, value.trim()])
        .filter(([, value]) => value),
    );
    const message = interaction.questions
      .filter((question) => clean[question.slot])
      .map((question) => `${question.prompt} ${clean[question.slot]}`)
      .join("، ");
    setSubmitted(true);
    try {
      await onAnswer(interactionId, clean, message);
    } catch {
      setSubmitted(false);
    }
  }

  async function dismiss() {
    setSubmitted(true);
    try {
      await onDismiss(interactionId);
    } catch {
      setSubmitted(false);
    }
  }

  return (
    <section
      className="w-full rounded-2xl border border-emerald-200 bg-emerald-50/40 p-4 shadow-sm"
      aria-labelledby={`interaction-${interactionId}-title`}
    >
      <h3
        id={`interaction-${interactionId}-title`}
        className="text-sm font-bold text-slate-900"
      >
        أكمل البيانات للمتابعة
      </h3>

      <div className="mt-4 space-y-4">
        {interaction.questions.map((question, index) => {
          const groupName = `interaction-${interactionId}-${question.slot}`;
          return (
            <fieldset key={question.slot} disabled={isDisabled}>
              <legend className="text-sm font-semibold text-slate-800">
                {index + 1}. {question.prompt}
                {question.required && (
                  <span className="text-red-600" aria-hidden="true">
                    {" "}
                    *
                  </span>
                )}
              </legend>
              {question.options.length > 0 && (
                <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {question.options.map((option) => (
                    <label
                      key={option.value}
                      className="flex cursor-pointer items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 hover:border-emerald-300"
                    >
                      <input
                        type="radio"
                        name={groupName}
                        value={option.value}
                        checked={answers[question.slot] === option.value}
                        onChange={() => selectOption(question.slot, option.value)}
                        className="size-4 accent-emerald-600"
                      />
                      {option.label}
                    </label>
                  ))}
                </div>
              )}
              {question.allow_custom && (
                <div className="mt-2">
                  <label
                    htmlFor={`${groupName}-custom`}
                    className="text-xs text-slate-500"
                  >
                    أو اكتب إجابة أخرى
                  </label>
                  <input
                    id={`${groupName}-custom`}
                    type="text"
                    value={custom[question.slot] ?? ""}
                    onChange={(event) =>
                      typeCustom(question.slot, event.target.value)
                    }
                    aria-describedby={error ? errorId : undefined}
                    aria-invalid={Boolean(error && !answers[question.slot])}
                    className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100"
                  />
                </div>
              )}
            </fieldset>
          );
        })}
      </div>

      {error && (
        <p id={errorId} role="alert" className="mt-3 text-sm text-red-700">
          {error}
        </p>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Button type="button" onClick={submit} disabled={isDisabled}>
          <Check className="size-4" aria-hidden="true" />
          إرسال
        </Button>
        <Button
          type="button"
          variant="ghost"
          onClick={dismiss}
          disabled={isDisabled}
        >
          <X className="size-4" aria-hidden="true" />
          إهمال
        </Button>
      </div>
    </section>
  );
}
