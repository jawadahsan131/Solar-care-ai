import { Suspense } from "react";
import { redirect } from "next/navigation";
import { connection } from "next/server";
import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import ChatbotClient from "./chatbot-client";

export default function ChatbotPage() {
  return (
    <Suspense fallback={<main className="app-shell"><div className="loading-panel">Loading chat…</div></main>}>
      <ChatbotContent />
    </Suspense>
  );
}

async function ChatbotContent() {
  await connection();
  const supabase = await createClient();
  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();
  if (error || !user) redirect("/login");

  return (
    <main className="app-shell min-h-screen px-4 pb-10">
      <header className="topbar">
        <Link className="brand-lockup" href="/dashboard">
          <span className="brand-mark">S</span> Solar Care AI
        </Link>
        <Link className="button button-quiet" href="/dashboard">All homes</Link>
      </header>
      <ChatbotClient />
    </main>
  );
}
