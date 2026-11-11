import { Suspense } from "react";
import PlanClient from "../plan/plan-client";

export default function HomeDashboardPage() {
  return (
    <Suspense fallback={<div className="loading-panel">Loading your dashboard…</div>}>
      <PlanClient dashboard />
    </Suspense>
  );
}
