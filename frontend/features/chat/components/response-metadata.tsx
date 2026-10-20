"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";

const LABELS: Record<string, string> = {
  intent: "النية",
  classified_by: "صُنِّفت بـ",
  classifier_task: "مهمة التصنيف",
  handled_by: "العقدة",
  response_source: "مصدر الرد",
  generator_role: "دور النموذج",
  nodes_path: "مسار التنفيذ",
  subgraph_nodes_executed: "عقد الرسم الفرعي",
  retrieval_used: "استُخدم الاسترجاع",
  quality_score: "درجة الجودة",
  recalled: "استدعاء ذاكرة",
  abuse_count: "عدد الإساءة",
  final_plan_generated: "وُلِّدت الخطة",
  retried_sections: "أقسام أُعيدت",
  section_needs_improvement: "قسم يحتاج تحسين",
};

const SOURCES: Record<string, string> = {
  llm: "نموذج لغوي",
  template: "نص جاهز",
  subgraph: "رسم فرعي",
};

function formatValue(value: unknown): string {
  // عرض قيمة الميتا داتا بنص مقروء.
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "نعم" : "لا";
  if (Array.isArray(value)) {
    return value.length > 0 ? value.map((item) => String(item)).join("، ") : "—";
  }
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export function ResponseMetadata({
  metadata,
}: {
  metadata: Record<string, unknown>;
}) {
  // لوحة مطوية تعرض ميتا داتا مصدر الرد لأغراض التتبع.
  const [open, setOpen] = useState(false);
  const entries = Object.entries(metadata).filter(([key]) => key !== "nodes_path");
  if (Object.keys(metadata).length === 0) return null;

  const handledBy =
    typeof metadata.handled_by === "string" ? metadata.handled_by : null;
  const path = Array.isArray(metadata.nodes_path)
    ? metadata.nodes_path.map((item) => String(item))
    : [];

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger className="flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[11px] text-slate-400 transition-colors hover:text-slate-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600/40">
        <ChevronDown
          className={cn("size-3 transition-transform", open && "rotate-180")}
          aria-hidden
        />
        <span>مصدر الرد</span>
        {handledBy && <span className="font-mono text-slate-500">{handledBy}</span>}
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="mt-1.5 w-72 max-w-[70vw] space-y-1 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-[11px] leading-5 text-slate-600">
          {path.length > 0 && (
            <p className="font-mono text-slate-500">{path.join(" ← ")}</p>
          )}
          {entries.map(([key, value]) => (
            <div key={key} className="flex items-start justify-between gap-3">
              <span className="shrink-0 font-medium">{LABELS[key] ?? key}</span>
              <span className="text-start font-mono break-all text-slate-500">
                {key === "response_source"
                  ? (SOURCES[String(value)] ?? formatValue(value))
                  : formatValue(value)}
              </span>
            </div>
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
