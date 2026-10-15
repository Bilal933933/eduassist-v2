import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "المساعد النحوي | EduAssist V2",
  description: "مساعد تعليمي ذكي للغة العربية",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="ar"
      dir="rtl"
      className="h-full antialiased"
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
