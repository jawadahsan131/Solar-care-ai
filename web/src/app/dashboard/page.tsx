import { Suspense } from "react";
import { redirect } from "next/navigation";
import { connection } from "next/server";
import { createClient } from "@/lib/supabase/server";
import DashboardClient from "./dashboard-client";

export default function DashboardPage() {
  return (
    <Suspense fallback={<main className="app-shell"><div className="loading-panel">Loading your home dashboard…</div></main>}>
      <DashboardContent />
    </Suspense>
  );
}

async function DashboardContent() {
  await connection();
  const supabase = await createClient();
  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();
  if (error || !user) redirect("/login");

  return <DashboardClient email={user.email ?? ""} />;
}
