"use client";

import { MonitorIcon, MoonIcon, SunIcon } from "lucide-react";
import { useTheme } from "next-themes";
import { useSyncExternalStore } from "react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const THEMES = [
  { value: "light", label: "فاتح", icon: SunIcon },
  { value: "dark", label: "داكن", icon: MoonIcon },
  { value: "system", label: "النظام", icon: MonitorIcon },
] as const;

// اشتراك فارغ: يكفي لمعرفة أننا على العميل دون إحداث حالة إضافية.
const subscribe = () => () => {};
const getClientSnapshot = () => true;
const getServerSnapshot = () => false;

// ─── مبدّل الثيم: فاتح / داكن / حسب النظام (next-themes + class على <html>) ───
export function ThemeToggle() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  // تجنّب اختلاف الترطيب: الثيم المحفوظ لا يُعرف إلا بعد الترطيب.
  const mounted = useSyncExternalStore(subscribe, getClientSnapshot, getServerSnapshot);

  const ActiveIcon = mounted && resolvedTheme === "dark" ? MoonIcon : SunIcon;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button
            variant="ghost"
            size="icon"
            className="shrink-0 rounded-xl text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-label="تغيير الثيم"
            title="تغيير الثيم"
          />
        }
      >
        <ActiveIcon className="size-5" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-36">
        <DropdownMenuRadioGroup
          value={mounted ? (theme ?? "system") : "system"}
          onValueChange={(value) => setTheme(String(value))}
        >
          {THEMES.map(({ value, label, icon: Icon }) => (
            <DropdownMenuRadioItem key={value} value={value} className="gap-2">
              <Icon className="size-4" />
              {label}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
