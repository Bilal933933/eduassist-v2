"use client";

import { useState } from "react";
import { Info, ChevronDown, Activity } from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";

const LABELS: Record<string, string> = {
  intent: "النية الأساسية",
  classified_by: "تم التصنيف عبر",
  classifier_task: "مهمة التصنيف",
  handled_by: "العقدة الحالية",
  response_source: "مصدر الإجابة",
  generator_role: "دور المساعد",
  nodes_path: "مسار المعالجة",
  subgraph_nodes_executed: "العقد المنفذة",
  retrieval_used: "استرجاع من الذاكرة",
  quality_score: "درجة الدقة",
  recalled: "مسترجع سابقاً",
  abuse_count: "مرات التكرار",
  final_plan_generated: "توليد الخطة",
  retried_sections: "إعادة المحاولة",
  section_needs_improvement: "تحسين الجودة",
};

const SOURCES: Record<string, string> = {
  llm: "نموذج ذكاء اصطناعي",
  template: "قالب ثابت",
  subgraph: "عملية معقدة",
};

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "مفعل" : "غير مفعل";
  if (Array.isArray(value)) {
    return value.length > 0 ? value.map((item) => String(item)).join(" ← ") : "—";
  }
  if (typeof value === "object") return "...";
  return String(value);
}

export function ResponseMetadata({
  metadata,
}: {
  metadata: Record<string, unknown>;
}) {
  const [open, setOpen] = useState(false);
  const entries = Object.entries(metadata).filter(
    ([key]) => !["nodes_path", "handled_by"].includes(key),
  );
  if (Object.keys(metadata).length === 0) return null;

  const handledBy =
    typeof metadata.handled_by === "string" ? metadata.handled_by : null;
  const path = Array.isArray(metadata.nodes_path)
    ? metadata.nodes_path.map((item) => String(item))
    : [];

  return (
    <Collapsible
      open={open}
      onOpenChange={setOpen}
      className="mt-4 flex w-full flex-col items-center"
    >
      <CollapsibleTrigger className="group flex items-center gap-2 rounded-full border border-slate-200/60 bg-white/50 px-4 py-1.5 text-[11px] font-medium text-slate-500 transition-all hover:border-slate-300 hover:bg-white hover:text-slate-700 focus-visible:outline-none">
        <Activity className="size-3 text-emerald-600" />
        <span>تتبع مسار المعالجة الذكي</span>
        <ChevronDown
          className={cn(
            "size-3 opacity-50 transition-transform group-hover:opacity-100",
            open && "rotate-180",
          )}
        />
      </CollapsibleTrigger>
      <CollapsibleContent className="w-full">
        <div className="mx-auto mt-3 w-full max-w-2xl rounded-2xl border border-slate-200/80 bg-slate-50/80 p-5 shadow-sm backdrop-blur-sm">
          {path.length > 0 && (
            <div className="mb-3">
              <p className="mb-1.5 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                <Info className="size-3" />
                مسار التنفيذ الذكي
              </p>
              <div className="flex flex-wrap items-center gap-1.5 font-mono text-[10px] text-slate-600">
                {path.map((node, i) => (
                  <span key={i} className="flex items-center gap-1.5">
                    <span className="rounded bg-white px-1.5 py-0.5 shadow-sm">
                      {node}
                    </span>
                    {i < path.length - 1 && (
                      <span className="text-slate-300">←</span>
                    )}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 gap-y-2.5">
            {entries.map(([key, value]) => (
              <div
                key={key}
                className="flex items-center justify-between border-b border-slate-200/40 pb-2 last:border-0 last:pb-0"
              >
                <span className="text-[11px] text-slate-500">
                  {LABELS[key] ?? key}
                </span>
                <span className="rounded-md bg-white/60 px-2 py-0.5 text-right font-mono text-[10px] font-medium text-slate-700 shadow-sm">
                  {key === "response_source"
                    ? (SOURCES[String(value)] ?? formatValue(value))
                    : formatValue(value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
