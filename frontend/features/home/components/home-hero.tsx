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
          <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-300">EduAssist V2</p>
          <h1 className="text-balance text-3xl font-bold text-foreground">المساعد النحوي</h1>
          <p className="text-pretty text-sm text-muted-foreground">
            مساعد تعليمي ذكي للغة العربية — اسأل عن القواعد واحفظ محادثاتك.
          </p>
          <Button
            className="w-full bg-emerald-700 dark:bg-emerald-600 text-white hover:bg-emerald-800 dark:hover:bg-emerald-500"
            onClick={() => router.push(userName ? "/chat" : "/login")}
          >
            {userName ? "ابدأ المحادثة" : "ابدأ الآن"}
          </Button>
        </CardContent>
      </Card>
      <div className="grid w-full grid-cols-1 gap-3 sm:grid-cols-3">
        {HIGHLIGHTS.map((item) => (
          <Card key={item.title}>
            <CardContent className="flex flex-col items-center gap-2 p-4 text-center">
              <item.icon className="size-6 text-emerald-700 dark:text-emerald-300" />
              <p className="text-sm font-bold text-foreground">{item.title}</p>
              <p className="text-xs leading-5 text-muted-foreground">{item.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
