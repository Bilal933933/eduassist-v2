import { redirect } from "next/navigation";

// ─── /chat وحده يحول لدردشة جديدة (القائمة الجانبية تعرض الأحدث) ───
export default function ChatIndexPage() {
  redirect("/chat/new");
}
