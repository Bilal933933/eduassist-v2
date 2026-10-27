"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider, useTheme } from "next-themes";
import { useState } from "react";
import { Toaster } from "sonner";

// الإشعارات تتبع الثيم الحالي (داخل ThemeProvider حتى يقرأ الثيم المحفوظ).
function ThemedToaster() {
  const { resolvedTheme } = useTheme();

  return (
    <Toaster
      richColors
      position="bottom-center"
      theme={(resolvedTheme ?? "system") as "light" | "dark" | "system"}
    />
  );
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
        {children}
        <ThemedToaster />
      </ThemeProvider>
    </QueryClientProvider>
  );
}
