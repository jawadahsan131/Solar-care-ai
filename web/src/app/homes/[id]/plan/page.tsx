import { Suspense } from "react";
import PlanClient from "./plan-client";

export default function PlanPage() {
  return (
    <Suspense fallback={<div className="loading-panel">Loading your solar plan…</div>}>
      <PlanClient />
    </Suspense>
  );
}
