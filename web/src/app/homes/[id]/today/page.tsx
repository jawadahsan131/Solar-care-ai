import { Suspense } from "react";
import TodayClient from "./today-client";

export default function TodayPage() {
  return (
    <Suspense fallback={<div className="loading-panel">Loading today’s estimate…</div>}>
      <TodayClient />
    </Suspense>
  );
}
