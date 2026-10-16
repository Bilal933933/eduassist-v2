"use client";

import { BookOpen, MessagesSquare, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const HIGHLIGHTS = [
  {
    icon: BookOpen,
    title: "شروح القواعد",
    description: "إجابات تعليمية منظمة في النحو والصرف.",
  },
  {
    icon: MessagesSquare,
    title: "محادثات محفوظة",
    description: "سجل كل نقاشاتك وارجع إليها في أي وقت.",
  },
  {
    icon: Sparkles,
    title: "ردود فورية",
    description: "بث لحظي للرد مع مؤشر كتابة حي.",
  },
];

export function HomeHero({ userName }: { userName?: string }) {
  const router = useRouter();

  return (
    <div className="flex w-full max-w-xl flex-col items-center gap-6">
      <Card className="w-full text-center">
        <CardContent className="space-y-4 p-8">
          <p className="text-sm font-semibold text-emerald-700">EduAssist V2</p>
          <h1 className="text-3xl font-bold text-slate-950">المساعد النحوي</h1>
          <p className="text-sm text-slate-500">
            مساعد تعليمي ذكي للغة العربية — اسأل عن القواعد واحفظ محادثاتك.
          </p>
          <Button
            className="w-full"
            onClick={() => router.push(userName ? "/chat" : "/login")}
          >
            {userName ? `أكمل كـ ${userName}` : "ابدأ الآن"}
          </Button>
        </CardContent>
      </Card>
      <div className="grid w-full grid-cols-1 gap-3 sm:grid-cols-3">
        {HIGHLIGHTS.map((item) => (
          <Card key={item.title}>
            <CardContent className="flex flex-col items-center gap-2 p-4 text-center">
              <item.icon className="size-6 text-emerald-700" />
              <p className="text-sm font-bold text-slate-900">{item.title}</p>
              <p className="text-xs leading-5 text-slate-500">{item.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
